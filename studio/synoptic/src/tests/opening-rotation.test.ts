// fix/opening-rotation (user, 2026-09-18: "błąd obrotu drzwi - sprawdź
// od razu geometryczną poprawność elementów pomieszczeń po obrotach"):
// rotation keeps a symbol's centre (Konva turns about the corner), an
// opening turns by flipping on its wall, and the doorway is cut where
// the door actually is - at its drawn (scaled) size.
import { describe, it, expect } from 'vitest';
import { useStore } from '../store';
import {
  effectiveSize, findWallOpenings, objectCenter, openingCutPolygon, openingFlipped, seatOpeningInWall,
  topLeftForCenter,
} from '../project/WallOpenings';
import type { SynopticObject } from '../store';
import type { WallElement } from '../elements/WallElement';

const wall = (id: string, from: [number, number], to: [number, number]): WallElement => ({
  id, from: { x: from[0], y: from[1] }, to: { x: to[0], y: to[1] }, thickness: 12,
} as unknown as WallElement);

/** A clockwise-on-screen room: top, right, bottom (right to left), left. */
const room = [wall('t', [100, 100], [580, 100]), wall('r', [580, 100], [580, 500]),
              wall('b', [580, 500], [100, 500]), wall('l', [100, 500], [100, 100])];

const obj = (id: string, type: string, extra: Partial<SynopticObject> = {}): SynopticObject => ({
  id, type, category: 'BUILDING', x: 0, y: 0, rotation: 0, scaleX: 1, scaleY: 1, visible: true, locked: false,
  layer: 1, tag: '', description: '', color: '', fill: '', border: '', text: '', font: '', fontSize: 12,
  tooltip: '', width: 60, height: 20, customProperties: {}, editor: {}, ...extra,
} as unknown as SynopticObject);

/** Where Konva puts a group's local point: translate(x, y) then rotate about the origin, scale applied first. */
function konvaPoint(o: SynopticObject, lx: number, ly: number): [number, number] {
  const rad = ((o.rotation || 0) * Math.PI) / 180;
  const sx = lx * (o.scaleX || 1), sy = ly * (o.scaleY || 1);
  return [o.x + sx * Math.cos(rad) - sy * Math.sin(rad), o.y + sx * Math.sin(rad) + sy * Math.cos(rad)];
}

const near = (a: number, b: number) => Math.abs(a - b) < 1e-6;

describe('opening rotation', () => {
  it('objectCenter is where Konva draws the centre, scale and rotation included', () => {
    for (const rotation of [0, 37, 90, 180, 270]) {
      const o = obj('c', 'building.chair', { x: 120, y: 80, width: 60, height: 20, scaleX: 2, scaleY: 1.5, rotation });
      const [kx, ky] = konvaPoint(o, 30, 10);
      const c = objectCenter(o);
      expect(near(c.x, kx) && near(c.y, ky)).toBe(true);
      const back = topLeftForCenter(c, effectiveSize(o).width, effectiveSize(o).height, rotation);
      expect(near(back.x, o.x) && near(back.y, o.y)).toBe(true);
    }
  });

  it("rotateSelected keeps a symbol's centre and steps 90 either way", () => {
    const chair = obj('c', 'building.chair', { x: 200, y: 200, width: 60, height: 20, scaleX: 1.5 });
    useStore.setState({ objects: [chair], walls: [], selectedIds: ['c'], selectedWallIds: [] });
    const before = objectCenter(chair);
    useStore.getState().rotateSelected('cw');
    let after = useStore.getState().objects[0];
    expect(after.rotation).toBe(90);
    expect(near(objectCenter(after).x, before.x) && near(objectCenter(after).y, before.y)).toBe(true);
    expect(after.x).not.toBe(chair.x);                                  // the origin moved, the centre did not
    useStore.getState().rotateSelected('ccw');
    useStore.getState().rotateSelected('ccw');
    after = useStore.getState().objects[0];
    expect(after.rotation).toBe(-90);
    expect(near(objectCenter(after).x, before.x) && near(objectCenter(after).y, before.y)).toBe(true);
  });

  it('a door on a wall turns by flipping its side and stays seated with its doorway under it', () => {
    const seatedDoor = (() => {
      const raw = obj('d', 'building.door', { x: 300, y: 492, width: 60, height: 20 });
      const seat = seatOpeningInWall(room, raw)!;
      return { ...raw, ...seat };
    })();
    expect(seatedDoor.rotation).toBe(180);                              // the bottom wall runs right to left
    const c0 = objectCenter(seatedDoor);
    expect(near(c0.y, 500)).toBe(true);
    useStore.setState({ objects: [seatedDoor], walls: room, selectedIds: ['d'], selectedWallIds: [] });

    useStore.getState().rotateSelected('cw');
    const flipped = useStore.getState().objects[0];
    expect(flipped.rotation).toBe(0);                                   // flipped, not turned across the wall
    const c1 = objectCenter(flipped);
    expect(near(c1.x, c0.x) && near(c1.y, 500)).toBe(true);
    const opening = findWallOpenings(room, [flipped])[0];
    expect(opening.wallId).toBe('b');
    expect(near(opening.center.x, c1.x) && near(opening.center.y, 500)).toBe(true);
    expect(opening.width).toBe(60);

    useStore.getState().rotateSelected('ccw');
    expect(useStore.getState().objects[0].rotation).toBe(180);          // and back
    expect(useStore.getState().objects[0].editor?.opening_flipped).toBe(false);
    expect(openingFlipped(0, 180)).toBe(true);
    expect(openingFlipped(170, 180)).toBe(false);
    expect(openingFlipped(-90, 0)).toBe(false);
  });

  it('a widened door cuts a doorway of its drawn width, centred where it is drawn', () => {
    const raw = obj('d', 'building.door', { x: 200, y: 92, width: 60, height: 20, scaleX: 2 });
    const seat = seatOpeningInWall(room, raw)!;
    const door = { ...raw, ...seat };
    expect(door.rotation).toBe(0);                                      // the top wall runs left to right
    expect(near(objectCenter(door).x, 260) && near(objectCenter(door).y, 100)).toBe(true);
    const opening = findWallOpenings(room, [door])[0];
    expect(opening.width).toBe(120);
    expect(near(opening.center.x, 260)).toBe(true);
    const xs = openingCutPolygon(opening).map(p => p.x);
    expect(near(Math.min(...xs), 200) && near(Math.max(...xs), 320)).toBe(true);

    // A moved door keeps its flipped side when re-seated; a fresh one takes the wall's own direction.
    const flippedDoor = { ...door, editor: { opening_flipped: true }, x: 330, y: 110 };
    expect(seatOpeningInWall(room, flippedDoor)!.rotation).toBe(180);
    const freshOnBottom = obj('f', 'building.door', { x: 300, y: 492, width: 60, height: 20, rotation: 0 });
    expect(seatOpeningInWall(room, freshOnBottom)!.rotation).toBe(180);
  });
});
