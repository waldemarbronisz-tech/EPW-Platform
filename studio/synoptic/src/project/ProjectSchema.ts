import type { SynopticObject, SynopticConnection } from '../store';
import type { MeterElement } from '../meter/MeterElement';
import type { SignalPanelElement } from '../elements/SignalPanelElement';
import type { FrameElement } from '../elements/FrameElement';
import type { GroupCommandElement } from '../elements/GroupCommandElement';
import type { SetpointPanelElement } from '../elements/SetpointElement';
import type { Device, LocationEntry, CardEntry } from './DeviceSchema';
import type { ScreenKind } from '../store';
import type { HelpLanguage } from '../i18n/HelpLanguage';
import { getSymbolDefinition } from '../symbols/SymbolRegistry';
import { COLOR_CANVAS_BACKGROUND, GRID_SIZE } from '../theme/ScadaTheme';

export interface EPWProjectInfo {
  name: string;
  description: string;
  created_at: string;
  modified_at: string;
}

export interface EPWCanvasSchema {
  width: number;
  height: number;
  background: string;
  gridSize?: number;
}

export interface EPWProjectSchema {
  format: string;
  schema_version: number;
  project: EPWProjectInfo;
  canvas: EPWCanvasSchema;
  objects: SynopticObject[];
  connections?: SynopticConnection[];
  // feat/meter-element part A: optional and additive, same as
  // connections above - an older project file simply has no meters
  // (loads as an empty array), not an invalid one. Does not warrant a
  // schema version bump, the same reasoning already applied to earlier
  // additive fields (boundaryDirection/boundaryMedium/boundaryPortSide
  // etc.).
  meters?: MeterElement[];
  // feat/editing-and-signal-panel commit 6: same treatment as meters
  // above - optional, additive, no schema version bump.
  signalPanels?: SignalPanelElement[];
  // feat/appearance-selection-frames commit 3: same treatment again -
  // a new kind of element in the EXISTING project shape, not a new
  // shape. Optional, additive, no schema version bump (GRANICE for
  // that task was explicit: if adding the frame element seemed to
  // need one, stop and report instead of bumping it - it does not).
  frames?: FrameElement[];
  // feat/meter-element part B: the project's device list, per src/
  // project/DeviceSchema.ts's contract (this editor's first caller of
  // it - see raport.md for the full read path). Just the flat device
  // array, not the full DeviceRegistry (locations/cards): nothing in
  // this editor manages locations or cards yet, and carrying them here
  // unused would be dead weight. Optional and additive for the same
  // reason meters is - no schema version bump.
  devices?: Device[];
  // feat/device-list-ui commit 1: the other two thirds of DeviceSchema.ts's
  // DeviceRegistry shape, now that this editor actually manages them - same
  // optional/additive treatment as devices above (an older file simply has
  // no locations/cards, not an invalid one). No schema version bump.
  locations?: LocationEntry[];
  cards?: CardEntry[];
  // Which screen kind this project is. Optional and additive: a file
  // with no `kind` field at all - every file saved before this concept
  // existed - is SCHEMATIC, exactly as it already behaved with no such
  // concept in the format at all. chore/remove-isometric-plan-mode:
  // SCHEMATIC is now the ONLY value this field is ever written with, or
  // that a NEW file will ever contain - the isometric PLAN mode this
  // field used to also allow has been removed entirely. The field
  // itself is deliberately kept (not deleted, and no schema version
  // bump) so an OLDER file saved with `kind: "PLAN"` still loads rather
  // than being rejected - see project/ProjectManager.ts's own loading
  // code for where that legacy value is converted to SCHEMATIC, with a
  // Messages-panel notice.
  kind?: ScreenKind;
  // feat/help-system commit 1: which language the Help window shows -
  // same optional/additive treatment as every field above (an older
  // file simply has no saved choice, defaulting to Polish - see
  // helpSlice.ts). No schema version bump: this is a preference, not
  // drawing content, the same category devices/locations/cards already
  // established.
  helpLanguage?: HelpLanguage;
  // feat/control-elements commit 2: the group command button - same
  // optional/additive treatment as every field above (an older project
  // file simply has no group command buttons, not an invalid one). No
  // schema version bump.
  groupCommands?: GroupCommandElement[];
  // feat/selector-symbol-setpoint-alarm: the setpoint panel - same
  // optional/additive treatment as groupCommands above.
  setpointPanels?: SetpointPanelElement[];
}

// v2: node-based wiring. A connection is a freehand orthogonal polyline
// (SynopticConnection.points), not a pair of ports - fromId/fromPort/
// toId/toPort are gone. See Migrations.ts for the v1 -> v2 conversion.
export const CURRENT_SCHEMA_VERSION = 2;
export const FORMAT_NAME = "EPW_SYNOPTIC";

// feat/isometric-engine commit 5: `kind` defaults to SCHEMATIC - every
// existing call site (and every existing test) that calls
// createEmptyProject(name) with one argument keeps creating exactly the
// screen it always did.
export function createEmptyProject(name: string = "New Project", kind: ScreenKind = 'SCHEMATIC'): EPWProjectSchema {
  return {
    format: FORMAT_NAME,
    schema_version: CURRENT_SCHEMA_VERSION,
    project: {
      name,
      description: "",
      created_at: new Date().toISOString(),
      modified_at: new Date().toISOString()
    },
    canvas: {
      width: 1920,
      height: 1080,
      background: COLOR_CANVAS_BACKGROUND,
      gridSize: GRID_SIZE
    },
    objects: [],
    connections: [],
    kind
  };
}

export interface ValidationIssue {
  severity: 'ERROR' | 'WARNING' | 'INFO';
  code: string;
  message: string;
  objectId?: string;
}

export interface ValidationResult {
  valid: boolean;
  issues: ValidationIssue[];
}

export function validateProjectSchema(data: any): ValidationResult {
  const issues: ValidationIssue[] = [];

  if (!data || typeof data !== 'object') {
     return { valid: false, issues: [{ severity: 'ERROR', code: 'INVALID_FORMAT', message: 'Data is not an object' }] };
  }

  if (data.format !== FORMAT_NAME) {
     issues.push({ severity: 'ERROR', code: 'INVALID_FORMAT', message: `Format must be ${FORMAT_NAME}` });
  }

  if (typeof data.schema_version !== 'number') {
     issues.push({ severity: 'ERROR', code: 'MISSING_VERSION', message: 'Missing schema_version' });
  } else if (data.schema_version > CURRENT_SCHEMA_VERSION) {
     issues.push({ severity: 'ERROR', code: 'UNSUPPORTED_VERSION', message: `Unsupported schema version: ${data.schema_version}. Max is ${CURRENT_SCHEMA_VERSION}` });
  }

  if (!data.project || typeof data.project.name !== 'string') {
     issues.push({ severity: 'ERROR', code: 'INVALID_PROJECT_META', message: 'Missing or invalid project.name' });
  }

  if (!data.canvas || typeof data.canvas.width !== 'number' || typeof data.canvas.height !== 'number') {
     issues.push({ severity: 'ERROR', code: 'INVALID_CANVAS', message: 'Missing or invalid canvas config' });
  }

  if (!Array.isArray(data.objects)) {
     issues.push({ severity: 'ERROR', code: 'INVALID_OBJECTS', message: 'Objects must be an array' });
     return { valid: false, issues };
  }

  const objectIds = new Set<string>();
  for (const obj of data.objects) {
    if (!obj.id) {
       issues.push({ severity: 'ERROR', code: 'MISSING_OBJ_ID', message: 'Object missing ID' });
       continue;
    }
    if (objectIds.has(obj.id)) {
       issues.push({ severity: 'ERROR', code: 'DUPLICATE_OBJ_ID', objectId: obj.id, message: `Duplicate object ID: ${obj.id}` });
    }
    objectIds.add(obj.id);

    const def = getSymbolDefinition(obj.type);
    if (!def) {
       issues.push({ severity: 'WARNING', code: 'UNKNOWN_SYMBOL', objectId: obj.id, message: `Unknown symbol type: ${obj.type}` });
    }
  }

  // Node-based wiring model (v2): a connection is a freehand polyline,
  // not a pair of ports - there is no fromId/toId left to dangle. What
  // replaces "does this connection reference a real object" is net-level
  // validation instead (NetResolver.validateNets, run separately - it
  // needs the full symbol registry's terminal geometry, which does not
  // belong in a plain schema-shape validator like this one).
  const connIds = new Set<string>();
  if (data.connections) {
    for (const conn of data.connections) {
      if (!conn.id) {
         issues.push({ severity: 'ERROR', code: 'MISSING_CONN_ID', message: 'Connection missing ID' });
         continue;
      }
      if (connIds.has(conn.id)) {
         issues.push({ severity: 'ERROR', code: 'DUPLICATE_CONN_ID', message: `Duplicate connection ID: ${conn.id}` });
      }
      connIds.add(conn.id);

      if (!Array.isArray(conn.points) || conn.points.length < 2) {
         issues.push({ severity: 'ERROR', code: 'TOO_FEW_POINTS', message: `Connection ${conn.id} needs at least 2 points, got ${Array.isArray(conn.points) ? conn.points.length : 0}` });
         continue;
      }

      for (const p of conn.points) {
        if (typeof p.x !== 'number' || typeof p.y !== 'number' || p.x % GRID_SIZE !== 0 || p.y % GRID_SIZE !== 0) {
           issues.push({ severity: 'ERROR', code: 'OFF_GRID_POINT', message: `Connection ${conn.id} has a point off the ${GRID_SIZE}px grid: (${p.x}, ${p.y})` });
        }
      }

      for (let i = 0; i < conn.points.length - 1; i++) {
        const a = conn.points[i];
        const b = conn.points[i + 1];
        if (a.x !== b.x && a.y !== b.y) {
           issues.push({ severity: 'ERROR', code: 'DIAGONAL_SEGMENT', message: `Connection ${conn.id} has a diagonal segment between points ${i} and ${i + 1} - only horizontal or vertical segments are allowed` });
        }
      }

      if (conn.medium !== 'ELECTRICAL' && conn.medium !== 'WATER' && conn.medium !== 'VENTILATION') {
         issues.push({ severity: 'ERROR', code: 'INVALID_MEDIUM', message: `Connection ${conn.id} has an invalid medium: ${conn.medium}` });
      }
      if (conn.style !== 'NORMAL' && conn.style !== 'BUS') {
         issues.push({ severity: 'ERROR', code: 'INVALID_STYLE', message: `Connection ${conn.id} has an invalid style: ${conn.style}` });
      }
      // feat/water-management commit 2: state is optional now (a
      // manual per-connection setting no longer exists - see
      // NetResolver.ts's own computed net state) - absent is valid,
      // same as every other optional field in this schema; an actual
      // garbage value is still an error.
      if (conn.state !== undefined && conn.state !== 'LIVE' && conn.state !== 'DEAD') {
         issues.push({ severity: 'ERROR', code: 'INVALID_STATE', message: `Connection ${conn.id} has an invalid state: ${conn.state}` });
      }
    }
  }

  const hasErrors = issues.some(i => i.severity === 'ERROR');
  return { valid: !hasErrors, issues };
}
