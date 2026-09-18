// fix/room-resize-precision (user, 2026-09-18: "rozciąganie pokoju działa
// nieprecyzyjnie"): the resize handles follow the POINTER, mapped through
// the stage's pan and zoom, instead of a Konva-dragged node that React kept
// putting back - so the dragged edge lands exactly under the mouse.
import { describe, it, expect } from 'vitest';
import { canvasPointFromClient, resizeBox, resizeByDelta } from '../project/GroupScale';
import handlesSource from '../components/canvas/GroupResizeHandles.tsx?raw';

describe('room resize precision', () => {
  it('maps a mouse position through the container offset, the pan and the zoom', () => {
    expect(canvasPointFromClient(300, 200, 100, 50, 0, 0, 1)).toEqual({ x: 200, y: 150 });
    expect(canvasPointFromClient(300, 200, 100, 50, 40, -10, 2)).toEqual({ x: 80, y: 80 });
    expect(canvasPointFromClient(300, 200, 0, 0, 0, 0, 0)).toEqual({ x: 300, y: 200 });   // a zero zoom never divides
  });

  it('the dragged edge lands exactly on the (snapped) pointer while the opposite edge stays put', () => {
    const before = { x: 100, y: 100, width: 200, height: 150 };
    const after = resizeBox(before, 'se', { x: 344, y: 296 });
    expect(after).toEqual({ x: 100, y: 100, width: 244, height: 196 });
    const west = resizeBox(before, 'w', { x: 60, y: 999 });
    expect(west).toEqual({ x: 60, y: 100, width: 240, height: 150 });
  });

  it('a slight move changes nothing and the opposite corner never moves, even with the room off the grid', () => {
    const room = { x: 100, y: 100, width: 480, height: 400 };          // corner at 580, not on a 16 px grid
    expect(resizeByDelta(room, 'se', { x: 3, y: 2 }, 16)).toEqual(room);
    expect(resizeByDelta(room, 'se', { x: 40, y: 40 }, 16)).toEqual({ x: 100, y: 100, width: 528, height: 448 });
    expect(resizeByDelta(room, 'se', { x: 40, y: 40 }, 0)).toEqual({ x: 100, y: 100, width: 520, height: 440 });
    expect(resizeByDelta(room, 'nw', { x: -16, y: 5 }, 16)).toEqual({ x: 84, y: 100, width: 496, height: 400 });
  });

  it('the store maps every endpoint exactly - the fixed edge stays where it was (source scan)', async () => {
    const { useStore } = await import('../store');
    useStore.setState({
      walls: [
        { id: 'w1', from: { x: 100, y: 100 }, to: { x: 580, y: 100 }, thickness: 12 },
        { id: 'w2', from: { x: 580, y: 100 }, to: { x: 580, y: 500 }, thickness: 12 },
        { id: 'w3', from: { x: 580, y: 500 }, to: { x: 100, y: 500 }, thickness: 12 },
        { id: 'w4', from: { x: 100, y: 500 }, to: { x: 100, y: 100 }, thickness: 12 },
      ] as never,
      selectedWallIds: ['w1', 'w2', 'w3', 'w4'], selectedIds: [], objects: [],
    });
    const before = { x: 100, y: 100, width: 480, height: 400 };
    useStore.getState().scaleSelection(before, resizeByDelta(before, 'se', { x: 40, y: 40 }, 16), 16);
    const walls = useStore.getState().walls;
    expect(walls.find(w => w.id === 'w1')!.from).toEqual({ x: 100, y: 100 });
    expect(walls.find(w => w.id === 'w2')!.to).toEqual({ x: 628, y: 548 });
    expect(walls.find(w => w.id === 'w4')!.to).toEqual({ x: 100, y: 100 });
  });

  it('the handles are no longer Konva-draggable nodes; the pointer drives them from window listeners', () => {
    expect(handlesSource).not.toMatch(/^\s*draggable\s*$/m);                 // no `draggable` prop on any node
    expect(handlesSource).toContain("window.addEventListener('mousemove', move)");
    expect(handlesSource).toContain('canvasPointFromClient(');
    expect(handlesSource).toContain('resizeByDelta(before, anchor, delta');
    expect(handlesSource).toContain('e.cancelBubble = true');
  });
});
