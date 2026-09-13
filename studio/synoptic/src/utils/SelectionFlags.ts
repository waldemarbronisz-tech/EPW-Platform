// Whether anything at all is selected - every kind of element, walls and
// frames included.
//
// Studio's shared toolbar enables Copy and Delete from this (the read-only
// state bridge in main.tsx). It used to count objects, wires and panels
// only, so a room selected with the marquee - walls, nothing else - left
// Copy and Delete greyed out in Studio.

export interface SelectionState {
  selectedIds: string[];
  selectedConnectionIds: string[];
  selectedMeterIds: string[];
  selectedSignalPanelIds: string[];
  selectedFrameIds: string[];
  selectedGroupCommandIds: string[];
  selectedSetpointPanelIds: string[];
  selectedWallIds: string[];
}

export function hasAnySelection(state: SelectionState): boolean {
  return (
    state.selectedIds.length > 0 ||
    state.selectedConnectionIds.length > 0 ||
    state.selectedMeterIds.length > 0 ||
    state.selectedSignalPanelIds.length > 0 ||
    state.selectedFrameIds.length > 0 ||
    state.selectedGroupCommandIds.length > 0 ||
    state.selectedSetpointPanelIds.length > 0 ||
    state.selectedWallIds.length > 0
  );
}
