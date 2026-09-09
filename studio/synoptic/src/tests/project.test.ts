import { describe, it, expect } from 'vitest';
import { validateProjectSchema, createEmptyProject } from '../project/ProjectSchema';
import { runMigrations } from '../project/Migrations';

describe('Project Schema Validation', () => {
  it('validates a fresh empty project', () => {
    const proj = createEmptyProject("Test Project");
    const result = validateProjectSchema(proj);
    expect(result.valid).toBe(true);
  });

  it('rejects invalid schema version', () => {
    const proj = createEmptyProject("Test");
    proj.schema_version = 999;
    const result = validateProjectSchema(proj);
    expect(result.valid).toBe(false);
    expect(result.issues[0].message).toContain('Unsupported schema version');
  });

  it('rejects duplicate object IDs', () => {
    const proj = createEmptyProject("Test");
    proj.objects = [
      { id: '123', type: 'electrical.busbar', x: 0, y: 0 } as any,
      { id: '123', type: 'electrical.circuit_breaker', x: 10, y: 10 } as any
    ];
    const result = validateProjectSchema(proj);
    expect(result.valid).toBe(false);
    expect(result.issues[0].message).toContain('Duplicate object ID');
  });

  it('rejects a connection with fewer than 2 points (node-based wiring model)', () => {
    const proj = createEmptyProject("Test");
    proj.connections = [{ id: 'conn1', points: [{ x: 0, y: 0 }], medium: 'ELECTRICAL', style: 'NORMAL', state: 'LIVE' }];
    const result = validateProjectSchema(proj);
    expect(result.valid).toBe(false);
    expect(result.issues.some(i => i.message.toLowerCase().includes('point'))).toBe(true);
  });

  it('rejects a connection point that is not on a grid node', () => {
    const proj = createEmptyProject("Test");
    proj.connections = [{ id: 'conn1', points: [{ x: 0, y: 0 }, { x: 17, y: 0 }], medium: 'ELECTRICAL', style: 'NORMAL', state: 'LIVE' }];
    const result = validateProjectSchema(proj);
    expect(result.valid).toBe(false);
    expect(result.issues.some(i => i.code === 'OFF_GRID_POINT')).toBe(true);
  });

  it('rejects a diagonal segment', () => {
    const proj = createEmptyProject("Test");
    proj.connections = [{ id: 'conn1', points: [{ x: 0, y: 0 }, { x: 16, y: 16 }], medium: 'ELECTRICAL', style: 'NORMAL', state: 'LIVE' }];
    const result = validateProjectSchema(proj);
    expect(result.valid).toBe(false);
    expect(result.issues.some(i => i.code === 'DIAGONAL_SEGMENT')).toBe(true);
  });

  it('migrates schema non-destructively', () => {
    const proj = createEmptyProject("Test");
    const migrated = runMigrations(proj);
    expect(migrated).toEqual(proj); // For now it's an identity map
  });
});
