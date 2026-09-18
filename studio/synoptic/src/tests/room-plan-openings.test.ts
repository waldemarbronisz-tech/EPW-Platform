// feat/room-plan: openings seated in walls, and the resize rule that
// makes a plan symbol redraw instead of stretch.
//
// Pure functions and source scans, the same split the other two
// room-plan test files use: WallOpenings.ts has no Konva in it so its
// geometry can be checked with exact numbers, while "the canvas wires
// it up this way" has no runnable harness in this codebase and is
// checked by reading the source, exactly as frame-element.test.ts
// established.

import { describe, it, expect } from 'vitest';
import type { WallElement } from '../elements/WallElement';
import { WALL_DEFAULT_THICKNESS } from '../elements/WallElement';
import {
  findWallOpenings, isOpeningType, openingCutPolygon, openingJambs,
  seatOpeningInWall, topLeftForCenter, wallForOpening,
} from '../project/WallOpenings';
import type { SynopticObject } from '../store';
import { SYMBOL_REGISTRY } from '../symbols/SymbolRegistry';
import { cm } from '../theme/Scale';

import objectNodeSource from '../components/canvas/ObjectNode.tsx?raw';
import wallLayerSource from '../components/WallLayer.tsx?raw';
import canvasSource from '../components/Canvas.tsx?raw';

const wall = (from: [number, number], to: [number, number], extra: Partial<WallElement> = {}): WallElement => ({
  id: `${from.join(',')}->${to.join(',')}`,
  from: { x: from[0], y: from[1] },
  to: { x: to[0], y: to[1] },
  thickness: WALL_DEFAULT_THICKNESS,
  ...extra,
});

const opening = (type: string, x: number, y: number, width = cm(90), height = cm(25)): SynopticObject => ({
  id: `${type}@${x},${y}`, type, category: 'BUILDING', x, y,
  rotation: 0, scaleX: 1, scaleY: 1, visible: true, locked: false, layer: 0,
  tag: '', description: '', color: '', fill: '', border: '', text: '', font: '', fontSize: 12,
  tooltip: '', width, height, customProperties: {},
});

// A horizontal wall along y = 100, from x = 0 to x = 400.
const TOP_WALL = wall([0, 100], [400, 100]);

describe('which wall an opening belongs to', () => {
  it('recognises door, window and gate - and nothing else', () => {
    expect(isOpeningType('building.door')).toBe(true);
    expect(isOpeningType('building.window')).toBe(true);
    expect(isOpeningType('building.gate')).toBe(true);
    // A socket is mounted ON a wall; it does not pierce it.
    expect(isOpeningType('building.socket_outlet')).toBe(false);
    expect(isOpeningType('building.table')).toBe(false);
  });

  it('takes an opening sitting on the wall', () => {
    // Centre of this door lands at (200, 100) - dead on the wall.
    const door = opening('building.door', 200 - cm(90) / 2, 100 - cm(25) / 2);
    expect(wallForOpening([TOP_WALL], door)?.id).toBe(TOP_WALL.id);
  });

  it('leaves an opening parked well away from any wall alone', () => {
    const door = opening('building.door', 0, 400);
    expect(wallForOpening([TOP_WALL], door)).toBeNull();
    expect(findWallOpenings([TOP_WALL], [door])).toEqual([]);
  });

  it('picks the NEAREST wall when an opening sits near a corner', () => {
    const left = wall([0, 100], [0, 400]);
    // Clearly closer to the horizontal wall than to the vertical one.
    const door = opening('building.door', 200 - cm(90) / 2, 100 - cm(25) / 2);
    expect(wallForOpening([left, TOP_WALL], door)?.id).toBe(TOP_WALL.id);
  });
});

describe('the hole cut in the wall', () => {
  const door = opening('building.door', 200 - cm(90) / 2, 100 - cm(25) / 2);
  const [found] = findWallOpenings([TOP_WALL], [door]);

  it('is centred on the wall line, not on wherever the symbol happened to sit', () => {
    expect(found.center.x).toBeCloseTo(200);
    expect(found.center.y).toBeCloseTo(100);
  });

  it('is as wide as the opening and deeper than the wall is thick', () => {
    const cut = openingCutPolygon(found);
    const xs = cut.map(p => p.x);
    const ys = cut.map(p => p.y);
    expect(Math.max(...xs) - Math.min(...xs)).toBeCloseTo(cm(90));
    // Deeper than the wall: a cut exactly as deep leaves a hairline of
    // wall paint across the opening from antialiasing.
    expect(Math.max(...ys) - Math.min(...ys)).toBeGreaterThan(WALL_DEFAULT_THICKNESS);
  });

  it('follows the WALL angle, so a diagonal wall still gets a square opening', () => {
    const diagonal = wall([0, 0], [200, 200]);
    const door = opening('building.door', 100 - cm(90) / 2, 100 - cm(25) / 2);
    const [cutOpening] = findWallOpenings([diagonal], [door]);
    expect(cutOpening.angle).toBeCloseTo(Math.PI / 4);
  });

  it('closes the cut with two jambs', () => {
    expect(openingJambs(found)).toHaveLength(2);
  });
});

describe('seating an opening into its wall', () => {
  it('centres it on the wall and turns it to the wall angle', () => {
    const door = opening('building.door', 180, 92);
    const seat = seatOpeningInWall([TOP_WALL], door)!;
    expect(seat).not.toBeNull();
    expect(seat.rotation).toBeCloseTo(0);
    // Its centre must land on the wall's own line (y = 100).
    expect(seat.y + cm(25) / 2).toBeCloseTo(100);
  });

  it('turns it to match a vertical wall', () => {
    const left = wall([0, 0], [0, 400]);
    // Unrotated the door is cm(90) wide, so its top-left must be half
    // that to the left of the wall for its centre to land on x = 0.
    const door = opening('building.door', -cm(90) / 2, 200);
    const seat = seatOpeningInWall([left], door)!;
    expect(Math.abs(seat.rotation)).toBeCloseTo(90);
  });

  it('leaves an opening that is on no wall exactly where it is', () => {
    expect(seatOpeningInWall([TOP_WALL], opening('building.door', 0, 500))).toBeNull();
  });

  it('stays seated in a wall drawn RIGHT TO LEFT - the rotated case', () => {
    // A wall drawn right-to-left has angle 180, so seating an opening
    // into it rotates the opening by 180 too. The object centre is then
    // NOT x + w/2: Konva turns a group about its own top-left origin.
    //
    // Getting that wrong made an opening stop being recognised as being
    // in the wall the instant it was seated into it, and the wall drew
    // unbroken straight through the door - visible only on walls drawn
    // in one particular direction, which is how it survived a look at
    // the screen. This is that case, pinned.
    const rightToLeft = wall([400, 100], [0, 100]);
    const dropped = opening('building.door', 200 - cm(90) / 2, 100 - cm(25) / 2);

    const seat = seatOpeningInWall([rightToLeft], dropped)!;
    expect(Math.abs(seat.rotation)).toBeCloseTo(180);

    const seated = { ...dropped, ...seat };
    // Still on the wall after being seated - the whole point.
    expect(wallForOpening([rightToLeft], seated)?.id).toBe(rightToLeft.id);
    expect(findWallOpenings([rightToLeft], [seated])).toHaveLength(1);
    // And centred on it, to the pixel.
    expect(findWallOpenings([rightToLeft], [seated])[0].center.y).toBeCloseTo(100);
  });

  it('the cut clears the whole PAINTED body, not just the footprint', () => {
    // The wall is drawn extruded up the screen, so a hole the size of
    // the footprint leaves the part that rises above it intact - sitting
    // directly over the opening.
    const door = opening('building.door', 200 - cm(90) / 2, 100 - cm(25) / 2);
    const [found] = findWallOpenings([TOP_WALL], [door]);
    const cut = openingCutPolygon(found);
    const topOfCut = Math.min(...cut.map(p => p.y));
    expect(found.wallDrawnHeight).toBeGreaterThan(0);
    expect(topOfCut).toBeLessThanOrEqual(100 - found.wallDrawnHeight);
  });

  it('topLeftForCenter is the inverse of "where is the centre"', () => {
    // Unrotated, the top-left is simply the centre minus half the size.
    expect(topLeftForCenter({ x: 100, y: 50 }, 40, 20, 0)).toEqual({ x: 80, y: 40 });
  });
});

describe('resize redraws a plan symbol instead of stretching it', () => {
  it('every BUDYNEK symbol declares resizeRedraws', () => {
    const types = Object.keys(SYMBOL_REGISTRY).filter(t => t.startsWith('building.'));
    expect(types.length).toBeGreaterThan(10);
    for (const type of types) {
      expect(SYMBOL_REGISTRY[type].resizeRedraws, type).toBe(true);
    }
  });

  it('no schematic symbol declares it - nothing else changes behaviour', () => {
    // The one deliberate exception: the SCADA text box (feat/text-
    // formatting). Stretching it would scale the glyphs; resizing it has
    // to re-flow the text in a bigger box, exactly like a plan symbol
    // redraws itself.
    const others = Object.keys(SYMBOL_REGISTRY).filter(t => !t.startsWith('building.') && t !== 'scada.text_box');
    expect(others.some(t => SYMBOL_REGISTRY[t].resizeRedraws)).toBe(false);
  });

  it('ObjectNode commits width/height (not scale) for such a symbol', () => {
    expect(objectNodeSource).toContain('resizeRedraws');
    // The branch must write real dimensions and reset the scale - a
    // resize that left scaleX/scaleY on the node would still stretch
    // the drawing, whatever it wrote to width/height.
    const branch = objectNodeSource.slice(objectNodeSource.indexOf('resizeRedraws'));
    expect(branch).toContain('width: resized.width');
    expect(branch).toContain('height: resized.height');
    expect(branch).toContain('scaleX: 1');
  });

  it('a ROTATED plan symbol is baked to width/height too, never left scaled (2026-09-18)', () => {
    const rotated = objectNodeSource.slice(objectNodeSource.indexOf('A ROTATED plan symbol resized'));
    expect(rotated).toContain("anchor !== 'rotater' && getSymbolDefinition(obj.type)?.resizeRedraws");
    expect(rotated).toContain('rotation: node.rotation(),');
    expect(rotated).toContain('scaleX: 1,');
  });
});

describe('wiring (source scan - no runnable harness for these)', () => {
  it('the wall body is clipped so openings are real holes', () => {
    expect(wallLayerSource).toContain('clipFunc');
    expect(wallLayerSource).toContain('openingCutPolygon');
  });

  it('jambs are drawn OUTSIDE the clipped body, or the hole would eat them', () => {
    // Anchored on where each is USED in the JSX, not on the import
    // lines at the top of the file - those appear in alphabetical-ish
    // order and say nothing about what is drawn when.
    const clipAt = wallLayerSource.indexOf('clipFunc={clipFunc}');
    const jambAt = wallLayerSource.indexOf('key={`jamb-');
    expect(clipAt).toBeGreaterThan(-1);
    expect(jambAt).toBeGreaterThan(clipAt);
  });

  it('the whole painted wall body takes clicks, not just its footprint', () => {
    // The footprint-only hit area is what made walls feel unclickable:
    // the wall you see is drawn lifted by its own height.
    expect(wallLayerSource).toContain('computeWallFaces');
    // The footprint AND the raised face - which is exactly what is
    // painted, now that the wall's top surface stays on the plan
    // instead of being lifted with the rest of the body.
    expect(wallLayerSource).toContain('faces.base');
    expect(wallLayerSource).toContain('faces.side');
  });

  it('an opening seats itself both when dropped and when dragged', () => {
    expect(canvasSource).toContain('seatOpeningInWall');
    expect(canvasSource).toContain('seatIfOpening');
  });
});
