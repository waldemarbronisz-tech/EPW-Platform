// feat/site-objects-2d commit 4 - mandatory test 9: grass and the
// concrete road lie in the background layer. Canvas.tsx has no unit
// tests of its own anywhere in this suite (it is a ~1000-line
// component, not a pure function) - see this test's own reasoning
// below for what IS mechanically checkable without a full Konva/DOM
// render, and raport.md for the live (Playwright) confirmation that a
// symbol placed on top of grass actually draws above it, matching
// PRZED ZGLOSZENIEM point 6.
//
// What ties a registry entry to "background layer" is the isSurface
// flag (SymbolRegistry.ts) - Canvas.tsx's own two object passes read
// exactly this flag (`objects.filter(obj => getSymbolDefinition(obj.
// type)?.isSurface)`, drawn first, right after the grid layer and
// before frames/connections/every other symbol; then the ordinary
// objects.map pass explicitly excludes it via the same flag) - so
// checking the flag IS checking the real mechanism, not a proxy for it.

import { describe, it, expect } from 'vitest';
import { getSymbolDefinition, getSymbolsByCategory } from '../symbols/SymbolRegistry';
// Read via Vite's own `?raw` suffix (same convention scada-symbols.test.ts/
// rotation-handle-removal.test.ts already use for scanning a known source
// file's own text), not Node's `fs`/`path`/`__dirname` - this tsconfig's
// own "types" list (tsconfig.app.json) has no Node globals at all.
import canvasSource from '../components/Canvas.tsx?raw';

describe('9. grass and concrete road lie in the background layer', () => {
  it('site.grass and site.concrete_road are both marked isSurface', () => {
    expect(getSymbolDefinition('site.grass')?.isSurface).toBe(true);
    expect(getSymbolDefinition('site.concrete_road')?.isSurface).toBe(true);
  });

  it('no other TEREN symbol is marked isSurface (only the two surfaces sit in the background layer)', () => {
    const teren = getSymbolsByCategory()['TEREN'] || [];
    const surfaces = teren.filter(def => def.isSurface);
    expect(surfaces.map(def => def.type).sort()).toEqual(['site.concrete_road', 'site.grass']);
  });

  it('Canvas.tsx actually reads isSurface to draw a background pass before every wire/ordinary symbol, and excludes it from the ordinary pass', () => {
    // The background pass (drawn before frames.map/connections.map).
    expect(canvasSource).toMatch(/objects\.filter\(\(obj\) => getSymbolDefinition\(obj\.type\)\?\.isSurface\)\.map/);
    // The ordinary pass explicitly excludes surfaces so nothing draws twice.
    expect(canvasSource).toMatch(/filter\(\(obj\) => !getSymbolDefinition\(obj\.type\)\?\.isSurface\)/);
    // The background pass must appear BEFORE frames.map in the file (same
    // "warstwa podkladu" position FrameElement itself uses) - textual
    // order in the source is exactly Konva's own draw order within one Layer.
    const surfacePassIndex = canvasSource.indexOf('isSurface)');
    const framesIndex = canvasSource.indexOf('frames.map((frame)');
    const connectionsIndex = canvasSource.indexOf('connections.map(conn');
    expect(surfacePassIndex).toBeGreaterThan(-1);
    expect(framesIndex).toBeGreaterThan(-1);
    expect(connectionsIndex).toBeGreaterThan(-1);
    expect(surfacePassIndex).toBeLessThan(framesIndex);
    expect(surfacePassIndex).toBeLessThan(connectionsIndex);
  });
});
