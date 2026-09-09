// Internal-audit fix (Canvas.tsx breakup): shared between Canvas.tsx
// itself and the sub-components split out of it (ObjectNode.tsx,
// ConnectionNode.tsx) - moved verbatim, comments included.

// feat/appearance-selection-frames commit 2c: group move. Dragging ANY
// selected element, when more than one thing is selected, moves the
// WHOLE selection together, keeping relative positions, as one history
// entry - "like a graphics program", per this commit's own spec. The
// store already has exactly the right primitive for this
// (moveSelectionBy, built for arrow-key movement: skips locked
// objects, touches all four kinds atomically, one saveHistory() call);
// Canvas.tsx's own groupDrag object just drives it from a mouse drag
// too, with a live visual follow for every OTHER selected element while
// the drag is in progress.
//
// A connection's own move-Group (ConnectionNode) has no absolute x/y of
// its own - its x/y IS a pending delta from its last committed points,
// reset to (0,0) after every drag - so a connection's own "position" for
// this purpose is always (0,0), never its points' own coordinates. Every
// other kind (object/meter/signal panel) is absolute, matching its own
// x/y field directly.
export type DragKey = string; // "obj:<id>" | "meter:<id>" | "panel:<id>" | "frame:<id>" | "groupcmd:<id>" | "conn:<id>"

export interface GroupDragApi {
  // Reports one element's own Konva node so ANOTHER element's leader
  // drag can reposition it live as a follower. Passing null
  // unregisters it (unmount).
  registerNode: (key: DragKey, node: any) => void;
  // Called from an element's own onDragStart. Starts a group drag only
  // when that element is part of a selection of MORE than one item;
  // otherwise clears any previous group-drag state so a lone drag
  // falls through to that element's own existing solo behavior.
  start: (key: DragKey) => void;
  isActive: () => boolean;
  // Called from the leader's own onDragMove with how far ITS OWN Konva
  // node has moved from where the drag started (raw, unsnapped - final
  // snapping happens once, together, at commit). Repositions every
  // OTHER selected element's Konva node by the same amount, display
  // only - nothing is written to the store until commit.
  follow: (dx: number, dy: number) => void;
  // Called from the leader's own onDragEnd with the final, already
  // grid-snapped delta. Writes the whole group to the store in one
  // moveSelectionBy call, resets every follower connection's move-
  // Group back to its neutral (0,0), and clears the group-drag state.
  commit: (dx: number, dy: number) => void;
}
