import type { StateCreator } from 'zustand';
import type { FrameElement } from '../elements/FrameElement';
import type { SynopticConnection } from './types';
import type { AppState } from './appState';
import { WALL_DEFAULT_THICKNESS, WALL_DEFAULT_HEIGHT, clampWallThickness, clampWallHeight } from '../elements/WallElement';
import { DEFAULT_WALL_MATERIAL } from '../theme/Materials';
import { DEFAULT_WORK_MODE, TOOL_MODE } from '../project/WorkModes';

// The canvas viewport and the currently-armed drawing tool (wire/frame/
// building) and its options - all UI/interaction state, none of it ever
// serialized into an .epwsyn file's objects/connections themselves.
export type ToolsSlice = Pick<AppState,
  | 'canvasState'
  | 'isDrawingConnection' | 'setDrawingMode'
  | 'isDrawingFrame' | 'drawingFrameVariant' | 'frameToolContinuous' | 'setDrawingFrameMode'
  | 'isDrawingWall' | 'isDrawingRoom' | 'wallDrawThickness' | 'wallDrawHeight' | 'wallDrawMaterial'
  | 'setDrawingWallMode' | 'setDrawingRoomMode' | 'setWallDrawThickness' | 'setWallDrawHeight' | 'setWallDrawMaterial'
  | 'previewMode' | 'setPreviewMode' | 'setFloorMaterial'
  | 'workMode' | 'setWorkMode'
  | 'showIlluminance' | 'setShowIlluminance'
  | 'editingTextId' | 'setEditingTextId' | 'nextTextFormat' | 'setNextTextFormat'
  | 'drawingMedium' | 'drawingStyle' | 'setDrawingMedium' | 'setDrawingStyle'
  | 'snapToGridEnabled' | 'toggleSnapToGrid'
  | 'wireRoutingMode' | 'setWireRoutingMode'
>;

export const createToolsSlice: StateCreator<AppState, [], [], ToolsSlice> = (set, get) => ({
  canvasState: { zoom: 1, panX: 0, panY: 0 },
  isDrawingConnection: false,
  isDrawingFrame: false,
  isDrawingWall: false,
  isDrawingRoom: false,
  wallDrawThickness: WALL_DEFAULT_THICKNESS,
  wallDrawHeight: WALL_DEFAULT_HEIGHT,
  wallDrawMaterial: DEFAULT_WALL_MATERIAL,
  previewMode: false,
  workMode: DEFAULT_WORK_MODE,
  showIlluminance: false,
  editingTextId: null,
  nextTextFormat: {},
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

  // feat/synoptic-modes: arming a tool switches to the work mode it
  // belongs to. The selection is left alone - editing is mode-
  // independent (WorkModes.ts header, user report "bez względu na tryb
  // edycja była możliwa cały czas"); switching modes used to drop
  // everything the new mode "could not reach".
  setWorkMode: (mode) => set((state) => ({
    workMode: mode,
    // A tool of another mode is put down: its tool button is no longer
    // on the toolbar, so a still-armed tool would be invisible.
    isDrawingConnection: mode === TOOL_MODE.wire ? state.isDrawingConnection : false,
    isDrawingWall: mode === TOOL_MODE.wall ? state.isDrawingWall : false,
    isDrawingRoom: mode === TOOL_MODE.room ? state.isDrawingRoom : false,
    isDrawingFrame: mode === TOOL_MODE.frame ? state.isDrawingFrame : false,
  })),

  setDrawingMode: (active) => {
    if (active) get().setWorkMode(TOOL_MODE.wire);
    set({ isDrawingConnection: active });
  },

  // Turning the frame tool on also turns the wire tool off (mutually
  // exclusive drawing tools, same as clicking the wire tool already
  // implicitly is the only such tool today) - a stray in-progress wire
  // drag and a frame drag fighting over the same mouse gesture would
  // be a genuine conflict, not just visual noise.
  setDrawingFrameMode: (active, variant, continuous) => {
    if (active) get().setWorkMode(TOOL_MODE.frame);
    set((state) => ({
    isDrawingFrame: active,
    drawingFrameVariant: variant || state.drawingFrameVariant,
    isDrawingConnection: active ? false : state.isDrawingConnection,
    // fix/handles-insert-mode-diodes commit 2: continuous is only ever
    // meaningful at the moment the tool is ARMED (active=true, Shift
    // was or wasn't held on the toolbar click that got us here) - once
    // turned off, always reset to false so a later plain (non-Shift)
    // re-arm never inherits a stale continuous flag from before.
    frameToolContinuous: active ? !!continuous : false
  }));
  },

  // Arming the wall tool turns the other two drawing tools off - three
  // tools fighting over the same mouse gesture would be a genuine
  // conflict, the same reasoning setDrawingFrameMode already applies.
  // It also leaves Podglad mode, which is not a drawing mode at all:
  // being armed to draw walls while clicks are meant to operate
  // circuits is a contradiction, not a combination.
  setDrawingWallMode: (active) => {
    if (active) get().setWorkMode(TOOL_MODE.wall);
    set((state) => ({
    isDrawingWall: active,
    isDrawingRoom: active ? false : state.isDrawingRoom,
    isDrawingConnection: active ? false : state.isDrawingConnection,
    isDrawingFrame: active ? false : state.isDrawingFrame,
    previewMode: active ? false : state.previewMode,
  }));
  },

  // The room tool is a DRAG, the wall tool is a chain of CLICKS - two
  // different gestures over the same canvas, so only one may be armed.
  setDrawingRoomMode: (active) => {
    if (active) get().setWorkMode(TOOL_MODE.room);
    set((state) => ({
    isDrawingRoom: active,
    isDrawingWall: active ? false : state.isDrawingWall,
    isDrawingConnection: active ? false : state.isDrawingConnection,
    isDrawingFrame: active ? false : state.isDrawingFrame,
    previewMode: active ? false : state.previewMode,
  }));
  },
  setWallDrawThickness: (thickness) => set({ wallDrawThickness: clampWallThickness(thickness) }),
  setWallDrawHeight: (height) => set({ wallDrawHeight: clampWallHeight(height) }),
  setWallDrawMaterial: (material) => set({ wallDrawMaterial: material }),
  setFloorMaterial: (material) => set((state) => ({
    canvasConfig: { ...state.canvasConfig, floorMaterial: material },
    isDirty: true,
  })),

  // Entering Podglad disarms every drawing tool, for the same reason
  // above: in Podglad a click operates the drawing instead of editing
  // it, so no tool may still be waiting to consume that click.
  setPreviewMode: (active) => set((state) => ({
    previewMode: active,
    // Leaving edit mode drops the edit selection: resize handles around
    // a fixture you are now operating rather than editing read as a
    // bug, and Delete would still act on it.
    ...(active ? {
      selectedIds: [], selectedConnectionIds: [], selectedMeterIds: [],
      selectedSignalPanelIds: [], selectedFrameIds: [], selectedGroupCommandIds: [],
      selectedSetpointPanelIds: [], selectedWallIds: [],
    } : {}),
    isDrawingConnection: active ? false : state.isDrawingConnection,
    isDrawingFrame: active ? false : state.isDrawingFrame,
    isDrawingWall: active ? false : state.isDrawingWall,
    isDrawingRoom: active ? false : state.isDrawingRoom,
  })),

  setShowIlluminance: (active) => set({ showIlluminance: active }),
  setEditingTextId: (id) => set({ editingTextId: id }),
  setNextTextFormat: (updates) => set((state) => ({ nextTextFormat: { ...state.nextTextFormat, ...updates } })),

  setDrawingMedium: (medium) => set({ drawingMedium: medium }),
  setDrawingStyle: (style) => set({ drawingStyle: style }),
  setWireRoutingMode: (mode) => set({ wireRoutingMode: mode }),

  toggleSnapToGrid: () => set((state) => ({ snapToGridEnabled: !state.snapToGridEnabled })),
});
