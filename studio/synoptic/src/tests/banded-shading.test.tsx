// feat/site-objects-2d commit 1: the shared banded-shading primitives
// (utils/site/BandedShading.tsx) are plain functions returning React
// elements - their own props are plain, inspectable objects, so this
// tests the exact geometry/proportions directly against
// docs/EPW_rysunki_referencja.py's own formulas, with no DOM/Konva
// rendering harness needed (same "test the pure data" convention this
// codebase already uses throughout).

import { describe, it, expect } from 'vitest';
import React from 'react';
import { bandedRect, bandedVRect, bandedCircle, glow } from '../symbols/site/BandedShading';
import {
  SITE_BAND_WIDTH, SITE_OUTLINE_WIDTH, SITE_GREY, SITE_RED, COLOR_LAMP_LIT, COLOR_OUTLINE
} from '../theme/ScadaTheme';

// Every primitive returns <Group>{...}</Group> - children as a flat
// array makes the rects/paths/circles easy to inspect by index.
function children(el: React.ReactElement): React.ReactElement[] {
  const kids = (el.props as { children: React.ReactNode }).children;
  const flat = React.Children.toArray(kids) as React.ReactElement[];
  // bandedRect's own conditional band wraps both band Rects in a single
  // Fragment child when band > 0 - flatten one level further so each
  // Rect is its own entry, matching bandedVRect/bandedCircle's own
  // already-flat shape.
  return flat.flatMap(child =>
    child.type === React.Fragment ? React.Children.toArray((child.props as { children: React.ReactNode }).children) as React.ReactElement[] : [child]
  );
}

describe('bandedRect', () => {
  it('draws the base fill plus a light band on top and a dark band on the bottom, using SITE_BAND_WIDTH/SITE_OUTLINE_WIDTH by default', () => {
    const el = bandedRect(10, 20, 100, 50, SITE_GREY);
    const kids = children(el);
    expect(kids.length).toBe(3); // base rect + light band + dark band

    const base = kids[0].props as any;
    expect(base.fill).toBe(SITE_GREY.base);
    expect(base.stroke).toBe(COLOR_OUTLINE);
    expect(base.strokeWidth).toBe(SITE_OUTLINE_WIDTH);

    const light = kids[1].props as any;
    expect(light.fill).toBe(SITE_GREY.light);
    expect(light.height).toBe(SITE_BAND_WIDTH);
    expect(light.y).toBe(20 + SITE_OUTLINE_WIDTH / 2); // top edge

    const dark = kids[2].props as any;
    expect(dark.fill).toBe(SITE_GREY.dark);
    expect(dark.height).toBe(SITE_BAND_WIDTH);
    expect(dark.y).toBe(20 + 50 - SITE_BAND_WIDTH - SITE_OUTLINE_WIDTH / 2); // bottom edge
  });

  it('band=0 skips both bands entirely - only the base fill remains', () => {
    const el = bandedRect(0, 0, 40, 20, SITE_RED, { band: 0 });
    const kids = children(el);
    expect(kids.length).toBe(1);
  });

  it('a custom band/outlineWidth overrides the ScadaTheme default', () => {
    const el = bandedRect(0, 0, 40, 20, SITE_RED, { band: 6, outlineWidth: 1.5 });
    const kids = children(el);
    expect((kids[0].props as any).strokeWidth).toBe(1.5);
    expect((kids[1].props as any).height).toBe(6);
  });
});

describe('bandedVRect', () => {
  it('always draws a light band on the left and a dark band on the right, unconditionally', () => {
    const el = bandedVRect(10, 10, 60, 80, SITE_GREY);
    const kids = children(el);
    expect(kids.length).toBe(3);
    const light = kids[1].props as any;
    const dark = kids[2].props as any;
    expect(light.fill).toBe(SITE_GREY.light);
    expect(light.x).toBe(10 + SITE_OUTLINE_WIDTH / 2); // left edge
    expect(dark.fill).toBe(SITE_GREY.dark);
    expect(dark.x).toBe(10 + 60 - SITE_BAND_WIDTH - SITE_OUTLINE_WIDTH / 2); // right edge
  });
});

describe('bandedCircle - light arc upper-left, shadow arc lower-right', () => {
  it('the light and shadow arc path data matches docs/EPW_rysunki_referencja.py\'s own C.circ() formula exactly', () => {
    const cx = 80, cy = 60, r = 20;
    const el = bandedCircle(cx, cy, r, SITE_GREY);
    const kids = children(el);
    expect(kids.length).toBe(3); // base circle + light arc + dark arc

    const base = kids[0].props as any;
    expect(base.fill).toBe(SITE_GREY.base);
    expect(base.radius).toBe(r);

    const lightArc = kids[1].props as any;
    expect(lightArc.data).toBe(`M${cx - r * 0.72},${cy - r * 0.5} A${r * 0.88},${r * 0.88} 0 0 1 ${cx + r * 0.1},${cy - r * 0.86}`);
    expect(lightArc.stroke).toBe(SITE_GREY.light);
    expect(lightArc.strokeWidth).toBe(r * 0.28);

    const darkArc = kids[2].props as any;
    expect(darkArc.data).toBe(`M${cx + r * 0.62},${cy + r * 0.5} A${r * 0.85},${r * 0.85} 0 0 1 ${cx - r * 0.2},${cy + r * 0.85}`);
    expect(darkArc.stroke).toBe(SITE_GREY.dark);
    expect(darkArc.strokeWidth).toBe(r * 0.22);
  });
});

describe('glow', () => {
  it('draws three concentric circles, radius shrinking as opacity rises toward the center, defaulting to COLOR_LAMP_LIT', () => {
    const el = glow(50, 50, 10);
    const kids = children(el);
    expect(kids.length).toBe(3);
    const [outer, mid, inner] = kids.map(k => k.props as any);
    expect(outer.radius).toBe(10 * 2.6);
    expect(outer.opacity).toBe(0.18);
    expect(mid.radius).toBe(10 * 1.8);
    expect(mid.opacity).toBe(0.28);
    expect(inner.radius).toBe(10 * 1.15);
    expect(inner.opacity).toBe(0.45);
    expect(outer.fill).toBe(COLOR_LAMP_LIT);
    expect(mid.fill).toBe(COLOR_LAMP_LIT);
    expect(inner.fill).toBe(COLOR_LAMP_LIT);
    // radius strictly shrinks, opacity strictly rises, moving inward
    expect(outer.radius).toBeGreaterThan(mid.radius);
    expect(mid.radius).toBeGreaterThan(inner.radius);
    expect(outer.opacity).toBeLessThan(mid.opacity);
    expect(mid.opacity).toBeLessThan(inner.opacity);
  });

  it('a custom color overrides the default', () => {
    const el = glow(0, 0, 5, { color: '#FF3030' });
    const kids = children(el);
    expect((kids[0].props as any).fill).toBe('#FF3030');
  });
});
