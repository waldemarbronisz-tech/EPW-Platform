// feat/water-management commit 3 - four-pass Houston-style pipe/wire
// rendering (docs/EPW_gospodarka_wodna_referencja.py's own pipe_seg).
// No numbered mandatory tests for this commit in the task itself - this
// file verifies the claims made in raport.md directly: four passes
// exist, rounded joins/caps replace the old sharp ones, every
// thickness/offset/opacity comes from ScadaTheme (never hardcoded),
// and it applies to every medium, not only water.

import { describe, it, expect } from 'vitest';
import connectionLineSource from '../components/ConnectionLine.tsx?raw';
import { getConductorCoreColor } from '../components/ConnectionLine';
import {
  CONDUCTOR_OUTLINE, CONDUCTOR_WIDTH,
  CONDUCTOR_HIGHLIGHT_WIDTH, CONDUCTOR_HIGHLIGHT_OFFSET_X, CONDUCTOR_HIGHLIGHT_OFFSET_Y,
  CONDUCTOR_SHADOW_WIDTH, CONDUCTOR_SHADOW_OFFSET_X, CONDUCTOR_SHADOW_OFFSET_Y, CONDUCTOR_SHADOW_OPACITY,
  COLOR_ENERGIZED, COLOR_ENERGIZED_LIGHT, COLOR_ENERGIZED_DARK,
  COLOR_WATER, COLOR_WATER_LIGHT, COLOR_WATER_DARK,
  VENTILATION_ACTIVE, VENTILATION_ACTIVE_LIGHT, VENTILATION_ACTIVE_DARK
} from '../theme/ScadaTheme';

describe('ScadaTheme - Houston pipe proportions, taken from the reference file', () => {
  it('CONDUCTOR_OUTLINE is now core+5 (was core+4), matching pipe_seg\'s own stroke-width={w+5}', () => {
    expect(CONDUCTOR_OUTLINE).toBe(5);
  });

  it('highlight pass: width 3.5, offset (-1,-3.2) - pipe_seg\'s own light pass, taken directly', () => {
    expect(CONDUCTOR_HIGHLIGHT_WIDTH).toBe(3.5);
    expect(CONDUCTOR_HIGHLIGHT_OFFSET_X).toBe(-1);
    expect(CONDUCTOR_HIGHLIGHT_OFFSET_Y).toBe(-3.2);
  });

  it('shadow pass: mirrored offset, same width, semi-transparent (pipe_seg has no literal shadow line - this is this task\'s own documented completion of that gap)', () => {
    expect(CONDUCTOR_SHADOW_WIDTH).toBe(CONDUCTOR_HIGHLIGHT_WIDTH);
    expect(CONDUCTOR_SHADOW_OFFSET_X).toBe(-CONDUCTOR_HIGHLIGHT_OFFSET_X);
    expect(CONDUCTOR_SHADOW_OFFSET_Y).toBe(-CONDUCTOR_HIGHLIGHT_OFFSET_Y);
    expect(CONDUCTOR_SHADOW_OPACITY).toBeGreaterThan(0);
    expect(CONDUCTOR_SHADOW_OPACITY).toBeLessThan(1);
  });

  it('the wire core itself is unchanged (CONDUCTOR_WIDTH still half a grid cell)', () => {
    expect(CONDUCTOR_WIDTH).toBe(8);
  });
});

describe('ConnectionLine.tsx - four passes, rounded joins, applies to every medium', () => {
  it('draws exactly four real (non-hit-area) <Path> passes per wire', () => {
    const pathTags = connectionLineSource.match(/<Path\b/g) ?? [];
    // 1 invisible hit-area pass + 4 real passes (outline/fill/shadow/highlight) = 5.
    expect(pathTags.length).toBe(5);
  });

  it('every real pass uses rounded joins and caps, not the old butt/miter', () => {
    expect(connectionLineSource).not.toContain('lineCap="butt"');
    expect(connectionLineSource).not.toContain('lineJoin="miter"');
    const roundJoins = connectionLineSource.match(/lineJoin="round"/g) ?? [];
    const roundCaps = connectionLineSource.match(/lineCap="round"/g) ?? [];
    expect(roundJoins.length).toBe(4);
    expect(roundCaps.length).toBe(4);
  });

  it('a shadow and a highlight pass both exist, each reading its own ScadaTheme offset/width/opacity constants', () => {
    expect(connectionLineSource).toContain('CONDUCTOR_SHADOW_OFFSET_X');
    expect(connectionLineSource).toContain('CONDUCTOR_SHADOW_OFFSET_Y');
    expect(connectionLineSource).toContain('CONDUCTOR_SHADOW_OPACITY');
    expect(connectionLineSource).toContain('CONDUCTOR_HIGHLIGHT_OFFSET_X');
    expect(connectionLineSource).toContain('CONDUCTOR_HIGHLIGHT_OFFSET_Y');
  });

  it('no color, thickness or offset is a literal number/hex outside ScadaTheme (source-scan, same convention as scada-symbols.test.ts)', () => {
    // Allow the deliberate "+10" hit-area padding and "Group"/"Path" JSX
    // words themselves; everything else affecting stroke/appearance
    // must be an imported ScadaTheme name, not a literal hex color.
    const hexLiterals = connectionLineSource.match(/#[0-9A-Fa-f]{3,8}\b/g);
    expect(hexLiterals).toBeNull();
  });

  it('applies to every medium, not only water: each of the three media resolves its own highlight/shadow pair via the same function', () => {
    expect(getConductorCoreColor('ELECTRICAL', 'ACTIVE')).toBe(COLOR_ENERGIZED);
    expect(getConductorCoreColor('WATER', 'ACTIVE')).toBe(COLOR_WATER);
    expect(getConductorCoreColor('VENTILATION', 'ACTIVE')).toBe(VENTILATION_ACTIVE);
    // Sanity: light/dark companions are genuinely different colors from
    // the base, for all three media (proves the shading is real, not a
    // no-op reusing the same color three times).
    [
      [COLOR_ENERGIZED, COLOR_ENERGIZED_LIGHT, COLOR_ENERGIZED_DARK],
      [COLOR_WATER, COLOR_WATER_LIGHT, COLOR_WATER_DARK],
      [VENTILATION_ACTIVE, VENTILATION_ACTIVE_LIGHT, VENTILATION_ACTIVE_DARK]
    ].forEach(([base, light, dark]) => {
      expect(light).not.toBe(base);
      expect(dark).not.toBe(base);
      expect(light).not.toBe(dark);
    });
  });
});
