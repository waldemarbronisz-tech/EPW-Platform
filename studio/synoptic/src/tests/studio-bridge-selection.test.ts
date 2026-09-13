// Studio enables its Copy and Delete buttons from the state bridge's
// hasSelection. Walls and frames were not counted, so a room selected
// with the marquee - walls only - could not be copied or deleted from
// Studio's toolbar.

import { describe, it, expect } from 'vitest';
import { hasAnySelection } from '../utils/SelectionFlags';
import mainSource from '../main.tsx?raw';

const none = {
  selectedIds: [], selectedConnectionIds: [], selectedMeterIds: [], selectedSignalPanelIds: [],
  selectedFrameIds: [], selectedGroupCommandIds: [], selectedSetpointPanelIds: [], selectedWallIds: [],
};

describe('hasSelection in the Studio state bridge', () => {
  it('is true for walls alone and for frames alone', () => {
    expect(hasAnySelection(none)).toBe(false);
    expect(hasAnySelection({ ...none, selectedWallIds: ['w1'] })).toBe(true);
    expect(hasAnySelection({ ...none, selectedFrameIds: ['f1'] })).toBe(true);
    expect(hasAnySelection({ ...none, selectedSetpointPanelIds: ['s1'] })).toBe(true);
  });

  it('is what the bridge reports, rather than a list of its own that can fall behind again', () => {
    expect(mainSource).toContain('hasSelection: hasAnySelection(s),');
  });
});
