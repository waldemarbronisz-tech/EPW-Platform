import { describe, it, expect } from 'vitest';
import { getMediaDefinition } from '../symbols/registry/MediaRegistry';

describe('Media Registry', () => {
  it('resolves correct styles', () => {
    const ac = getMediaDefinition('electrical_ac');
    expect(ac?.visualStyle.strokeColor).toBe('#e74c3c');
  });

  it('resolves rs485 domain data', () => {
    const m = getMediaDefinition('rs485');
    expect(m?.domain).toBe('data');
  });
});
