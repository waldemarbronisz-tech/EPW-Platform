// Internal-audit fix (Canvas.tsx breakup): the momentary Alt/Space key
// state used to be two plain module-level `let`s inside Canvas.tsx
// itself. Extracting ObjectNode/ConnectionNode into their own files (see
// src/components/canvas/) means they need this same live key state too -
// same cross-file plumbing problem ResizeHandles.ts's own
// getActiveResizeAnchor/setActiveResizeAnchor already solves for the
// active resize anchor, and the same fix: a shared module, not a React
// state value, because every drag handler needs the CURRENT key state at
// the instant a drag ends, not one captured in a stale closure or
// re-rendered prop - and a keypress should never by itself trigger a
// re-render of the whole canvas.
let altPressed = false;
let spacePressed = false;

export function isAltKeyDown(): boolean {
  return altPressed;
}
export function setAltKeyDown(pressed: boolean): void {
  altPressed = pressed;
}

export function isSpaceKeyDown(): boolean {
  return spacePressed;
}
export function setSpaceKeyDown(pressed: boolean): void {
  spacePressed = pressed;
}
