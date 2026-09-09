import { describe, it, expect } from 'vitest';
import { runMigrations } from '../project/Migrations';
import { validateProjectSchema, FORMAT_NAME } from '../project/ProjectSchema';
import { GRID_SIZE } from '../theme/ScadaTheme';

/**
 * A real v1 (.epwsyn, schema_version 1) project file - the exact shape
 * ProjectManager.getProjectData() used to write and ProjectManager.
 * loadProject() used to read, before this task. Two electrical.circuit_
 * breaker objects (IN at fraction 0.5,0 / OUT at 0.5,1 on a 40x40
 * canvas) joined by one old-model, port-based connection.
 */
function realV1ProjectFixture() {
  return {
    format: FORMAT_NAME,
    schema_version: 1,
    project: { name: 'Legacy Panel', description: 'A real v1 file', created_at: '2024-01-01T00:00:00.000Z', modified_at: '2024-01-01T00:00:00.000Z' },
    canvas: { width: 1920, height: 1080, background: '#00CFCF', gridSize: GRID_SIZE },
    objects: [
      {
        id: 'obj-q1', type: 'electrical.circuit_breaker', category: 'Electrical',
        x: 0, y: 0, rotation: 0, scaleX: 1, scaleY: 1,
        visible: true, locked: false, layer: 1,
        tag: 'electrical.circuit_breaker_1', designation: '-Q1', description: '',
        color: '#000', fill: '#c0c0c0', border: '#000',
        text: '', font: 'Arial', fontSize: 12, tooltip: '',
        width: 40, height: 40, customProperties: {}
      },
      {
        id: 'obj-k1', type: 'electrical.circuit_breaker', category: 'Electrical',
        x: 100, y: 100, rotation: 0, scaleX: 1, scaleY: 1,
        visible: true, locked: false, layer: 1,
        tag: 'electrical.circuit_breaker_2', designation: '-K1', description: '',
        color: '#000', fill: '#c0c0c0', border: '#000',
        text: '', font: 'Arial', fontSize: 12, tooltip: '',
        width: 40, height: 40, customProperties: {}
      }
    ],
    connections: [
      { id: 'conn-1', fromId: 'obj-q1', fromPort: 'OUT', toId: 'obj-k1', toPort: 'IN', type: 'electrical_ac' }
    ]
  };
}

describe('Migration v1 -> v2 on a real v1 project file', () => {
  it('bumps schema_version to 2', () => {
    const migrated = runMigrations(realV1ProjectFixture());
    expect(migrated.schema_version).toBe(2);
  });

  it('converts the port-based connection into a grid-aligned, orthogonal polyline', () => {
    const migrated: any = runMigrations(realV1ProjectFixture());
    expect(migrated.connections.length).toBe(1);

    const conn = migrated.connections[0];
    expect(conn.id).toBe('conn-1');
    expect(Array.isArray(conn.points)).toBe(true);
    expect(conn.points.length).toBeGreaterThanOrEqual(2);

    // Every point on the grid.
    conn.points.forEach((p: { x: number; y: number }) => {
      expect(p.x % GRID_SIZE).toBe(0);
      expect(p.y % GRID_SIZE).toBe(0);
    });

    // Every segment horizontal or vertical.
    for (let i = 0; i < conn.points.length - 1; i++) {
      const a = conn.points[i];
      const b = conn.points[i + 1];
      expect(a.x === b.x || a.y === b.y).toBe(true);
    }

    // fromObj's OUT port (0.5,1 fraction on a 40x40 box at x=0,y=0) is
    // world (20,40), snapped to (16,48) - the migrated polyline's first point.
    expect(conn.points[0]).toEqual({ x: 16, y: 48 });
    // toObj's IN port (0.5,0 fraction on a 40x40 box at x=100,y=100) is
    // world (120,100), snapped to (128,96) - the polyline's last point.
    expect(conn.points[conn.points.length - 1]).toEqual({ x: 128, y: 96 });
  });

  it('carries the medium, style and state over correctly', () => {
    const migrated: any = runMigrations(realV1ProjectFixture());
    const conn = migrated.connections[0];
    expect(conn.medium).toBe('ELECTRICAL');
    expect(conn.style).toBe('NORMAL'); // neither endpoint is a busbar
    expect(conn.state).toBe('LIVE'); // no DEENERGIZED preview_state on the source file
  });

  it('the migrated project validates cleanly against the v2 schema', () => {
    const migrated = runMigrations(realV1ProjectFixture());
    const result = validateProjectSchema(migrated);
    expect(result.valid).toBe(true);
  });

  it('a water connection migrates to medium WATER', () => {
    const fixture = realV1ProjectFixture();
    fixture.connections[0].type = 'water';
    const migrated: any = runMigrations(fixture);
    expect(migrated.connections[0].medium).toBe('WATER');
  });

  it('a de-energized connection migrates to state DEAD', () => {
    const fixture: any = realV1ProjectFixture();
    fixture.connections[0].editor = { preview_state: 'DEENERGIZED' };
    const migrated: any = runMigrations(fixture);
    expect(migrated.connections[0].state).toBe('DEAD');
  });

  it('a connection touching a busbar-type object migrates to style BUS', () => {
    const fixture: any = realV1ProjectFixture();
    fixture.objects[1].type = 'scada.busbar';
    fixture.objects[1].width = 200;
    fixture.objects[1].height = 22;
    fixture.connections[0].toPort = 'dyn_top_50';
    const migrated: any = runMigrations(fixture);
    expect(migrated.connections.length).toBe(1);
    expect(migrated.connections[0].style).toBe('BUS');
  });

  it('a connection with a dangling fromId is dropped, not migrated into an invalid shape', () => {
    const fixture = realV1ProjectFixture();
    fixture.connections[0].fromId = 'does-not-exist';
    const migrated: any = runMigrations(fixture);
    expect(migrated.connections.length).toBe(0);
  });

  it('an already-v2 project is left untouched (migration is version-gated)', () => {
    const v2Project = {
      format: FORMAT_NAME,
      schema_version: 2,
      project: { name: 'Already v2', description: '', created_at: '', modified_at: '' },
      canvas: { width: 1920, height: 1080, background: '#00CFCF', gridSize: GRID_SIZE },
      objects: [],
      connections: [{ id: 'c1', points: [{ x: 0, y: 0 }, { x: 16, y: 0 }], medium: 'ELECTRICAL', style: 'NORMAL', state: 'LIVE' }]
    };
    const migrated = runMigrations(v2Project);
    expect(migrated).toEqual(v2Project);
  });
});
