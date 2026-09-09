// fix/handles-insert-mode-diodes commit 2: insert tools return to
// select mode after placing an element (9), Shift held when a tool is
// chosen keeps it armed for continuous placement (10), Escape exits
// insert mode back to select (11). Same "test the store action /
// pure function, not the DOM event" convention as
// selection-and-keyboard.test.ts - no Konva/RTL rendering harness
// exists in this codebase (see raport.md) for actually firing a
// KeyboardEvent or a Konva mouse gesture at Canvas.tsx, so the RULE
// itself is unit-tested directly (shouldExitInsertModeAfterPlacing,
// the store's own setDrawingFrameMode/setDrawingMode transitions),
// and Canvas.tsx's own raw source is scanned to confirm its Escape
// handler actually calls the exact store actions this file proves
// behave correctly - the real end-to-end keyboard/mouse behavior was
// additionally verified live via Playwright (see raport.md, [E]).

import { describe, it, expect, beforeEach } from 'vitest';
import { shouldExitInsertModeAfterPlacing } from '../utils/InsertMode';
import { useStore } from '../store';
import canvasSource from '../components/Canvas.tsx?raw';

function resetStore() {
  useStore.setState({
    isDrawingConnection: false,
    isDrawingFrame: false,
    drawingFrameVariant: 'PLAIN',
    frameToolContinuous: false,
    frames: [],
    history: [{ objects: [], connections: [], meters: [], signalPanels: [], frames: [] }],
    historyIndex: 0
  });
}

describe('shouldExitInsertModeAfterPlacing - the pure rule behind 9 and 10', () => {
  // 9. after placing an element, mode returns to select (no Shift = not continuous)
  it('returns true (exit to select) when continuous mode was not enabled', () => {
    expect(shouldExitInsertModeAfterPlacing(false)).toBe(true);
  });

  // 10. placing with Shift held leaves the tool active (continuous mode)
  it('returns false (stay armed) when continuous mode was enabled', () => {
    expect(shouldExitInsertModeAfterPlacing(true)).toBe(false);
  });
});

describe('setDrawingFrameMode - continuous flag round-trips through the store (9, 10)', () => {
  beforeEach(resetStore);

  it('a plain (non-Shift) activation leaves frameToolContinuous false', () => {
    useStore.getState().setDrawingFrameMode(true, 'PLAIN', false);
    expect(useStore.getState().isDrawingFrame).toBe(true);
    expect(useStore.getState().frameToolContinuous).toBe(false);
  });

  it('a Shift activation sets frameToolContinuous true', () => {
    useStore.getState().setDrawingFrameMode(true, 'PLAIN', true);
    expect(useStore.getState().isDrawingFrame).toBe(true);
    expect(useStore.getState().frameToolContinuous).toBe(true);
  });

  it('turning the tool off always resets frameToolContinuous, even if it was true', () => {
    useStore.getState().setDrawingFrameMode(true, 'PLAIN', true);
    useStore.getState().setDrawingFrameMode(false);
    expect(useStore.getState().isDrawingFrame).toBe(false);
    expect(useStore.getState().frameToolContinuous).toBe(false);
  });

  it('9: simulates the exact placement sequence Canvas.tsx runs (addFrame then conditionally exit) - a plain activation returns to select after one placement', () => {
    useStore.getState().setDrawingFrameMode(true, 'PLAIN', false);
    useStore.getState().addFrame({ x: 0, y: 0, width: 64, height: 64, titlePosition: 'TOP_LEFT', variant: 'PLAIN' });
    if (shouldExitInsertModeAfterPlacing(useStore.getState().frameToolContinuous)) {
      useStore.getState().setDrawingFrameMode(false);
    }
    expect(useStore.getState().isDrawingFrame).toBe(false);
    expect(useStore.getState().frames.length).toBe(1);
  });

  it('10: the same sequence with Shift/continuous mode leaves the tool armed after placing', () => {
    useStore.getState().setDrawingFrameMode(true, 'PLAIN', true);
    useStore.getState().addFrame({ x: 0, y: 0, width: 64, height: 64, titlePosition: 'TOP_LEFT', variant: 'PLAIN' });
    if (shouldExitInsertModeAfterPlacing(useStore.getState().frameToolContinuous)) {
      useStore.getState().setDrawingFrameMode(false);
    }
    expect(useStore.getState().isDrawingFrame).toBe(true);
    expect(useStore.getState().frames.length).toBe(1);

    // and placing a SECOND one still leaves it armed - genuinely continuous
    useStore.getState().addFrame({ x: 100, y: 100, width: 64, height: 64, titlePosition: 'TOP_LEFT', variant: 'PLAIN' });
    if (shouldExitInsertModeAfterPlacing(useStore.getState().frameToolContinuous)) {
      useStore.getState().setDrawingFrameMode(false);
    }
    expect(useStore.getState().isDrawingFrame).toBe(true);
    expect(useStore.getState().frames.length).toBe(2);
  });
});

describe('Escape exits insert mode back to select (11)', () => {
  beforeEach(resetStore);

  it('setDrawingMode(false) turns off the wire tool from an active state', () => {
    useStore.getState().setDrawingMode(true);
    expect(useStore.getState().isDrawingConnection).toBe(true);
    useStore.getState().setDrawingMode(false);
    expect(useStore.getState().isDrawingConnection).toBe(false);
  });

  it('setDrawingFrameMode(false) turns off the frame/building tool from an active state', () => {
    useStore.getState().setDrawingFrameMode(true, 'BUILDING');
    expect(useStore.getState().isDrawingFrame).toBe(true);
    useStore.getState().setDrawingFrameMode(false);
    expect(useStore.getState().isDrawingFrame).toBe(false);
  });

  // Canvas.tsx's own Escape handler is a DOM keydown listener - no
  // Konva/RTL harness exists to fire a real KeyboardEvent at it (see
  // this file's own header). What CAN be verified directly is that
  // its source actually calls the two store actions proven above to
  // work, inside the Escape branch, and that it no longer merely
  // clears the selection unconditionally the way it used to.
  it('Canvas.tsx\'s Escape branch calls both setDrawingMode(false) and setDrawingFrameMode(false)', () => {
    const escapeBranch = canvasSource.slice(
      canvasSource.indexOf("if (e.key === 'Escape')"),
      canvasSource.indexOf("else if (e.key === 'Enter'")
    );
    expect(escapeBranch).toContain('s.setDrawingMode(false)');
    expect(escapeBranch).toContain('s.setDrawingFrameMode(false)');
  });
});
