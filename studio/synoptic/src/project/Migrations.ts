import type { EPWProjectSchema } from './ProjectSchema';
export { CURRENT_SCHEMA_VERSION } from './ProjectSchema';
import { resolveConnectionPoint, getAbsolutePortPosition } from '../utils/GeometryUtils';
import { getSymbolDefinition } from '../symbols/SymbolRegistry';
import { GRID_SIZE } from '../theme/ScadaTheme';

function snapToGrid(v: number): number {
  return Math.round(v / GRID_SIZE) * GRID_SIZE;
}

/**
 * v1 -> v2 (node-based wiring): a connection used to be a pair of ports
 * (fromId/fromPort/toId/toPort). v2 has no ports at all - a connection
 * is a freehand polyline instead. Each old connection becomes a straight
 * (or, when its two endpoints do not already share an x or y, a
 * one-bend) polyline, computed from where its old ports actually
 * resolved to and rounded onto the grid.
 *
 * This deliberately reuses GeometryUtils.resolveConnectionPoint and
 * getAbsolutePortPosition UNCHANGED rather than re-deriving the math:
 * that pair is the one place left in the codebase that still knows how
 * a v1 file's port ids resolve to a pixel position (dyn_ busbar ports,
 * the boundary point's per-instance PORT, every static connectionPoints
 * fraction) - a real, non-trivial computation this migration would
 * otherwise have to duplicate.
 *
 * A connection whose object or port no longer resolves (a dangling
 * fromId/toId, or a port id the target symbol no longer has) is
 * dropped rather than guessed at - there is no sensible polyline to
 * draw for it, and migrating v1 data into an invalid v2 shape would be
 * worse than losing that one connection.
 */
function migrateConnectionV1ToV2(conn: any, objects: any[]): any | null {
  if (!conn || typeof conn !== 'object') return null;

  const fromObj = objects.find((o: any) => o && o.id === conn.fromId);
  const toObj = objects.find((o: any) => o && o.id === conn.toId);
  if (!fromObj || !toObj) return null;

  const fromPort = resolveConnectionPoint(fromObj, conn.fromPort);
  const toPort = resolveConnectionPoint(toObj, conn.toPort);
  if (!fromPort || !toPort) return null;

  const p1 = getAbsolutePortPosition(fromObj, fromPort);
  const p2 = getAbsolutePortPosition(toObj, toPort);

  const x1 = snapToGrid(p1.x);
  const y1 = snapToGrid(p1.y);
  const x2 = snapToGrid(p2.x);
  const y2 = snapToGrid(p2.y);

  const points = (x1 === x2 || y1 === y2)
    ? [{ x: x1, y: y1 }, { x: x2, y: y2 }]
    // Not already aligned - one right-angle bend, horizontal leg first
    // out of the source port (the same convention the old orthogonal
    // router used).
    : [{ x: x1, y: y1 }, { x: x2, y: y1 }, { x: x2, y: y2 }];

  const isBus = !!(getSymbolDefinition(fromObj.type)?.supportsDynamicPorts || getSymbolDefinition(toObj.type)?.supportsDynamicPorts);

  return {
    id: conn.id || `migrated-${Math.random().toString(36).slice(2)}`,
    points,
    medium: conn.type === 'water' ? 'WATER' : 'ELECTRICAL',
    style: isBus ? 'BUS' : 'NORMAL',
    state: conn.editor?.preview_state === 'DEENERGIZED' ? 'DEAD' : 'LIVE'
  };
}

function migrateV1ToV2(data: any): any {
  const objects = Array.isArray(data.objects) ? data.objects : [];
  const oldConnections = Array.isArray(data.connections) ? data.connections : [];

  const migratedConnections = oldConnections
    .map((c: any) => migrateConnectionV1ToV2(c, objects))
    .filter((c: any) => c !== null);

  return {
    ...data,
    schema_version: 2,
    connections: migratedConnections
  };
}

export const runMigrations = (data: any): EPWProjectSchema => {
  let migrated = { ...data };

  // Example migration from unversioned to version 1
  if (!migrated.schema_version) {
    migrated.schema_version = 1;
    if (!migrated.format) migrated.format = "EPW_SYNOPTIC";
    if (!migrated.project) {
      migrated.project = {
        name: "Imported Project",
        description: "",
        created_at: new Date().toISOString(),
        modified_at: new Date().toISOString()
      };
    }
  }

  if (migrated.schema_version === 1) {
    migrated = migrateV1ToV2(migrated);
  }

  return migrated as EPWProjectSchema;
};
