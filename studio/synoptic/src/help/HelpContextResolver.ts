// feat/help-system commit 2 - THE one place that maps "what is currently
// selected" to "which help topic F1 should open" (task's own explicit
// requirement: "Mapowanie rodzaju elementu na rozdzial trzymaj w JEDNYM
// miejscu, nie rozsiane po komponentach"). Nothing else in this codebase
// may duplicate this decision - App.tsx's F1 handler calls this and
// nothing more.

import type { SynopticObject } from '../store/types';

export interface ContextualSelectionState {
  selectedIds: string[];
  selectedConnectionIds: string[];
  selectedMeterIds: string[];
  selectedSignalPanelIds: string[];
  selectedFrameIds: string[];
  objects: SynopticObject[];
}

/** Checked in this order because a real selection is always exactly one KIND at a time in this editor (PropertyInspector.tsx's own selectionKindCount rule) - order only matters for the pathological case of stale/mixed state, where picking any one deterministically beats picking none. */
export function getContextualHelpTopic(state: ContextualSelectionState): string {
  if (state.selectedConnectionIds.length > 0) return 'sch-drawing-wire';
  if (state.selectedMeterIds.length > 0) return 'elem-meter';
  if (state.selectedSignalPanelIds.length > 0) return 'elem-signal-panel';
  if (state.selectedFrameIds.length > 0) return 'elem-frame-building';

  if (state.selectedIds.length > 0) {
    const obj = state.objects.find(o => o.id === state.selectedIds[0]);
    if (obj?.type === 'scada.boundary_point') return 'elem-boundary-point';
    if (obj?.type === 'scada.indicator_diode') return 'elem-indicator-diode';
    if (obj?.type === 'scada.meter') return 'elem-meter';
    return 'sym-library';
  }

  // Mandatory test 8: F1 with nothing selected opens the introductory topic.
  return 'intro-what';
}
