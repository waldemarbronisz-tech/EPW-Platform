// fix/handles-insert-mode-diodes commit 2: insert tools return to
// select mode after placing an element. The RULE itself is a single,
// pure, Konva/DOM-free decision (kept separate and unit-tested the
// same way utils/ResizeHandles.ts's own resize math is, per this
// codebase's own convention - no Konva/RTL rendering harness exists
// here, so anything that CAN be pure is pulled out and tested as
// such; the actual wiring - which store action fires when, and the
// real keyboard/mouse events that trigger it - lives in
// Canvas.tsx/Toolbar.tsx/store.ts, verified live via Playwright
// instead (see raport.md).
//
// Default (continuousModeEnabled=false): after ONE placement, the
// tool must return to select - this is the fix's own headline
// requirement, since a tool staying armed indefinitely is exactly the
// reported bug (every subsequent click silently placing another
// element). Holding Shift when the tool was chosen flips this to
// continuous mode: the tool stays armed so several elements can be
// placed in a row without re-selecting the tool each time.
export function shouldExitInsertModeAfterPlacing(continuousModeEnabled: boolean): boolean {
  return !continuousModeEnabled;
}
