import { describe, it, expect } from 'vitest';
import { validateProjectSchema, createEmptyProject } from '../project/ProjectSchema';

describe('Advanced Project Validation', () => {
  it('rejects missing format', () => {
    const proj = createEmptyProject();
    (proj as any).format = undefined;
    expect(validateProjectSchema(proj).valid).toBe(false);
  });

  it('accepts correct missing connections array', () => {
    const proj = createEmptyProject();
    delete proj.connections;
    expect(validateProjectSchema(proj).valid).toBe(true);
  });
});
