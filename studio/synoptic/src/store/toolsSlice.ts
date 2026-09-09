import type { StateCreator } from 'zustand';
import type { FrameElement } from '../elements/FrameElement';
import type { SynopticConnection } from './types';
import type { AppState } from './appState';

// The canvas viewport and the currently-armed drawing tool (wire/frame/
// building) and its options - all UI/interaction state, none of it ever
// serialized into an .epwsyn file's objects/connections themselves.
export type ToolsSlice = Pick<AppState,
  | 'canvasState'
  | 'isDrawingConnection' | 'setDrawingMode'
  | 'isDrawingFrame' | 'drawingFrameVariant' | 'frameToolContinuous' | 'setDrawingFrameMode'
  | 'drawingMedium' | 'drawingStyle' | 'setDrawingMedium' | 'setDrawingStyle'
  | 'snapToGridEnabled' | 'toggleSnapToGrid'
  | 'wireRoutingMode' | 'setWireRoutingMode'
>;

export const createToolsSlice: StateCreator<AppState, [], [], ToolsSlice> = (set) => ({
  canvasState: { zoom: 1, panX: 0, panY: 0 },
  isDrawingConnection: false,
  isDrawingFrame: false,
  drawingFrameVariant: 'PLAIN' as FrameElement['variant'],
  frameToolContinuous: false,
  snapToGridEnabled: true,
  drawingMedium: 'ELECTRICAL' as SynopticConnection['medium'],
  drawingStyle: 'NORMAL' as SynopticConnection['style'],
  // feat/wire-routing-around-obstacles commit 3, point (a): which of
  // the two drawing modes a NEW wire is drawn with - AVOID by default,
  // per this task's own spec. Session-only UI state, exactly like
  // drawingMedium/drawingStyle above (same slice, same convention) -
  // never written into a saved project file (ProjectManager.ts's own
  // getProjectData lists its fields explicitly; this is deliberately
  // not one of them - test 23).
  wireRoutingMode: 'AVOID' as 'STRAIGHT' | 'AVOID',

  setDrawingMode: (active) => set({
    isDrawingConnection: active
  }),

  // Turning the frame tool on also turns the wire tool off (mutually
  // exclusive drawing tools, same as clicking the wire tool already
  // implicitly is the only such tool today) - a stray in-progress wire
  // drag and a frame drag fighting over the same mouse gesture would
  // be a genuine conflict, not just visual noise.
  setDrawingFrameMode: (active, variant, continuous) => set((state) => ({
    isDrawingFrame: active,
    drawingFrameVariant: variant || state.drawingFrameVariant,
    isDrawingConnection: active ? false : state.isDrawingConnection,
    // fix/handles-insert-mode-diodes commit 2: continuous is only ever
    // meaningful at the moment the tool is ARMED (active=true, Shift
    // was or wasn't held on the toolbar click that got us here) - once
    // turned off, always reset to false so a later plain (non-Shift)
    // re-arm never inherits a stale continuous flag from before.
    frameToolContinuous: active ? !!continuous : false
  })),

  setDrawingMedium: (medium) => set({ drawingMedium: medium }),
  setDrawingStyle: (style) => set({ drawingStyle: style }),
  setWireRoutingMode: (mode) => set({ wireRoutingMode: mode }),

  toggleSnapToGrid: () => set((state) => ({ snapToGridEnabled: !state.snapToGridEnabled })),
});
