// fix/room-resize-precision (user, 2026-09-18: "rozciąganie pokoju działa
// nieprecyzyjnie"): the resize handles follow the POINTER, mapped through
// the stage's pan and zoom, instead of a Konva-dragged node that React kept
// putting back - so the dragged edge lands exactly under the mouse.
import { describe, it, expect } from 'vitest';
import { canvasPointFromClient, resizeBox } from '../project/GroupScale';
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

  it('the handles are no longer Konva-draggable nodes; the pointer drives them from window listeners', () => {
    expect(handlesSource).not.toMatch(/^\s*draggable\s*$/m);                 // no `draggable` prop on any node
    expect(handlesSource).toContain("window.addEventListener('mousemove', move)");
    expect(handlesSource).toContain('canvasPointFromClient(');
    expect(handlesSource).toContain('e.cancelBubble = true');
  });
});
