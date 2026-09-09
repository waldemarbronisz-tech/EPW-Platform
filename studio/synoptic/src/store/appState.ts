// Internal-audit fix (god-file breakup): the combined store shape, moved
// out of store.ts unchanged so every slice creator (objectsSlice.ts,
// selectionSlice.ts, etc.) can type itself as
// `StateCreator<AppState, [], [], ItsOwnSlice>` - Zustand's own
// documented "slices" pattern - without a circular VALUE import back to
// store.ts (this file has no runtime code in it at all, only the type).
import type { MeterElement } from '../meter/MeterElement';
import type { SignalPanelElement } from '../elements/SignalPanelElement';
import type { FrameElement } from '../elements/FrameElement';
import type { GroupCommandElement } from '../elements/GroupCommandElement';
import type { SetpointPanelElement } from '../elements/SetpointElement';
import type { Device, LocationEntry, CardEntry } from '../project/DeviceSchema';
import type { CanvasState, DeviceCreateOrAssignRequest, DeviceFormRequest, HistorySnapshot, Message, ScreenKind, SynopticConnection, SynopticObject } from './types';
import type { HelpLanguage } from '../i18n/HelpLanguage';

export interface AppState {
  projectMetadata: {
    description: string;
    created_at: string;
    modified_at: string;
  };
  canvasConfig: {
    width: number;
    height: number;
    background: string;
    gridSize: number;
  };
  objects: SynopticObject[];
  connections: SynopticConnection[];
  // The meter element (feat/meter-element): its own array, deliberately
  // separate from objects - it is not a symbol, has no terminals, and
  // its height is never user-set (see MeterElement.ts).
  meters: MeterElement[];
  // The signal panel element (feat/editing-and-signal-panel commit 6):
  // the same mechanism as the meter, its own array - see
  // elements/SignalPanelElement.ts.
  signalPanels: SignalPanelElement[];
  // The frame element (feat/appearance-selection-frames commit 3): a
  // pure graphic (no terminals, no state, no aparat link) drawn by
  // dragging a rectangle - see elements/FrameElement.ts.
  frames: FrameElement[];
  // The group command button (feat/control-elements commit 2): a
  // screen-level convenience that re-issues one existing SWITCHED
  // command (.CLOSE/.OPEN) to a configurable list of devices at once -
  // see elements/GroupCommandElement.ts's own header for why this is
  // not new control logic.
  groupCommands: GroupCommandElement[];
  // The setpoint panel element (feat/selector-symbol-setpoint-alarm): the
  // same mechanism as the meter, for MODULATED devices instead of
  // MEASURED ones - see elements/SetpointElement.ts's own header for
  // why this is design-time layout only, never a live control.
  setpointPanels: SetpointPanelElement[];
  selectedIds: string[];
  selectedConnectionIds: string[];
  selectedMeterIds: string[];
  selectedSignalPanelIds: string[];
  selectedFrameIds: string[];
  selectedGroupCommandIds: string[];
  selectedSetpointPanelIds: string[];
  canvasState: CanvasState;
  clipboard: SynopticObject[];
  clipboardMeters: MeterElement[];
  clipboardSignalPanels: SignalPanelElement[];
  clipboardFrames: FrameElement[];
  clipboardGroupCommands: GroupCommandElement[];
  clipboardSetpointPanels: SetpointPanelElement[];
  clipboardConnections: SynopticConnection[];
  history: HistorySnapshot[];
  historyIndex: number;

  // Project State
  projectName: string;
  fileName: string | null;
  fileHandle: FileSystemFileHandle | null;
  isDirty: boolean;
  messages: Message[];

  // feat/meter-element part B: the project's device list (src/project/
  // DeviceSchema.ts's contract) - the first thing in this editor that
  // ever reads it. Read-only from every UI's perspective (the meter's
  // device picker, MeterResolver.ts); nothing here authors or edits a
  // device - see ProjectManager.ts for how this round-trips with a
  // project file, and raport.md for the full path description.
  devices: Device[];

  // feat/device-list-ui commit 1: the other two thirds of DeviceSchema.ts's
  // own DeviceRegistry shape (locations, cards) - devices themselves stay
  // declared above (they predate this slice); these two plus every CRUD
  // action across all three live in deviceRegistrySlice.ts. A device's own
  // config lives ONLY here, once - a screen element (Commit 5's "Aparat"
  // property) never stores anything but the id it points at.
  locations: LocationEntry[];
  cards: CardEntry[];
  addLocation: (entry: LocationEntry) => void;
  updateLocation: (code: string, entry: LocationEntry) => void;
  deleteLocation: (code: string) => void;
  addCard: (entry: CardEntry) => void;
  updateCard: (id: string, entry: CardEntry) => void;
  deleteCard: (id: string) => void;
  addDevice: (device: Device) => void;
  updateDevice: (id: string, device: Device) => void;
  deleteDevice: (id: string) => void;

  // Connection Drawing Mode
  isDrawingConnection: boolean;
  setDrawingMode: (active: boolean) => void;

  // Frame Drawing Mode (commit 3): active while the "Rysuj ramke"/
  // "Rysuj budynek" toolbar tool is toggled on - a drag on empty
  // canvas then draws a frame rectangle instead of a rubber-band
  // selection box. drawingFrameVariant is which of the two the next
  // drag creates; the tool stays active across multiple drags, same
  // convention as the wire tool above, until toggled off again.
  isDrawingFrame: boolean;
  drawingFrameVariant: FrameElement['variant'];
  // fix/handles-insert-mode-diodes commit 2: whether Shift was held
  // when this tool was last armed - true means the tool stays active
  // after placing one frame/building (continuous mode, for placing
  // several in a row); false (the default) means placing one returns
  // straight to select mode, per this fix's own required behavior.
  frameToolContinuous: boolean;
  setDrawingFrameMode: (active: boolean, variant?: FrameElement['variant'], continuous?: boolean) => void;

  // feat/media-and-proportions part C: the medium/style a NEW wire is
  // drawn with, chosen up front in the toolbar rather than after the
  // fact in Properties - it still applies to every newly drawn wire
  // until changed again, and can still be edited per-wire afterward.
  drawingMedium: SynopticConnection['medium'];
  drawingStyle: SynopticConnection['style'];
  setDrawingMedium: (medium: SynopticConnection['medium']) => void;
  setDrawingStyle: (style: SynopticConnection['style']) => void;

  // feat/wire-routing-around-obstacles commit 3, point (a): PROSTO (the
  // user places every bend by hand, today's existing behavior) or
  // OMIJAJ (a new wire's route is computed automatically around
  // obstacles, WireRouter.ts) - AVOID by default. Session-only, same
  // as drawingMedium/drawingStyle above: never written into a saved
  // project file.
  wireRoutingMode: 'STRAIGHT' | 'AVOID';
  setWireRoutingMode: (mode: 'STRAIGHT' | 'AVOID') => void;

  // Grid snapping: a persistent toggle (View menu, default on) separate
  // from the momentary Alt-key bypass, which lives outside the store
  // entirely (Canvas.tsx tracks the live key state directly).
  snapToGridEnabled: boolean;
  toggleSnapToGrid: () => void;

  // Actions
  setProjectName: (name: string) => void;
  setFileName: (name: string | null) => void;
  setFileHandle: (handle: FileSystemFileHandle | null) => void;
  setDirty: (dirty: boolean) => void;
  addMessage: (text: string) => void;

  setCanvasState: (state: Partial<CanvasState>) => void;
  addObject: (obj: Omit<SynopticObject, 'id'>) => void;
  updateObject: (id: string, updates: Partial<SynopticObject>) => void;
  updateObjects: (updates: {id: string, updates: Partial<SynopticObject>}[]) => void;
  addConnection: (conn: Omit<SynopticConnection, 'id'>) => void;
  updateConnection: (id: string, updates: Partial<SynopticConnection>) => void;
  addMeter: (meter: Omit<MeterElement, 'id'>) => void;
  updateMeter: (id: string, updates: Partial<MeterElement>) => void;
  addSignalPanel: (panel: Omit<SignalPanelElement, 'id'>) => void;
  updateSignalPanel: (id: string, updates: Partial<SignalPanelElement>) => void;
  addFrame: (frame: Omit<FrameElement, 'id'>) => void;
  updateFrame: (id: string, updates: Partial<FrameElement>) => void;
  addGroupCommand: (el: Omit<GroupCommandElement, 'id'>) => void;
  updateGroupCommand: (id: string, updates: Partial<GroupCommandElement>) => void;
  addSetpointPanel: (panel: Omit<SetpointPanelElement, 'id'>) => void;
  updateSetpointPanel: (id: string, updates: Partial<SetpointPanelElement>) => void;
  deleteObjects: (ids: string[], connIds?: string[], meterIds?: string[], signalPanelIds?: string[], frameIds?: string[], groupCommandIds?: string[], setpointPanelIds?: string[]) => void;
  // feat/wire-routing-around-obstacles commit 3, point (f): PRZELICZ
  // TRASE - recomputes the route of every given (selected) connection
  // around the screen's CURRENT obstacles, skipping any wire already
  // marked isManualRoute. On demand only, never automatic (point (e):
  // a move never triggers this on its own) - one saveHistory() call
  // for the whole batch, per this task's own "jeden wpis w historii"
  // requirement.
  recalculateConnectionRoutes: (ids: string[]) => void;
  selectObjects: (ids: string[], multi?: boolean) => void;
  selectConnections: (ids: string[], multi?: boolean) => void;
  selectMeters: (ids: string[], multi?: boolean) => void;
  selectSignalPanels: (ids: string[], multi?: boolean) => void;
  selectFrames: (ids: string[], multi?: boolean) => void;
  selectGroupCommands: (ids: string[], multi?: boolean) => void;
  selectSetpointPanels: (ids: string[], multi?: boolean) => void;
  // commit 3 (feat/editing-and-signal-panel), extended in commit 2
  // (feat/appearance-selection-frames) with a fifth kind, in
  // feat/control-elements commit 2 with a sixth, and in
  // feat/selector-symbol-setpoint-alarm with a seventh: replaces the
  // whole selection with a mix of all seven kinds at once (the
  // rubber-band's own result) - and Ctrl+A's "select everything on screen".
  selectMixed: (selection: { objectIds?: string[]; connectionIds?: string[]; meterIds?: string[]; signalPanelIds?: string[]; frameIds?: string[]; groupCommandIds?: string[]; setpointPanelIds?: string[] }) => void;
  selectAll: () => void;
  clearSelection: () => void;
  // Arrow keys (commit 3): every selected object/meter/signalPanel/
  // frame/connection moves by (dx, dy) together, as one history entry
  // per keypress.
  moveSelectionBy: (dx: number, dy: number) => void;

  // Clipboard
  copySelected: () => void;
  paste: () => void;
  duplicateSelected: () => void;
  // Alt+drag: a silent, unselected, no-history-entry-of-its-own clone
  // left at the dragged item's own current position, the instant the
  // drag starts - the item the user is actually dragging then keeps
  // moving as it normally would, so the drag's own eventual saveHistory
  // covers both the new clone and the move as ONE history entry.
  duplicateObjectInPlace: (id: string) => void;
  duplicateMeterInPlace: (id: string) => void;
  duplicateSignalPanelInPlace: (id: string) => void;
  duplicateFrameInPlace: (id: string) => void;
  duplicateGroupCommandInPlace: (id: string) => void;
  duplicateSetpointPanelInPlace: (id: string) => void;

  // History
  undo: () => void;
  redo: () => void;
  saveHistory: () => void;

  // Z-Index
  bringToFront: () => void;
  sendToBack: () => void;

  // Layout Tools
  alignSelected: (alignment: 'left' | 'center' | 'right' | 'top' | 'middle' | 'bottom') => void;
  distributeSelected: (axis: 'horizontal' | 'vertical') => void;

  // Lock/Unlock
  lockSelected: () => void;
  unlockSelected: () => void;

  // Rotation
  rotateSelected: (direction: 'cw' | 'ccw') => void;

  // Screen kind (chore/remove-isometric-plan-mode): SCHEMATIC is the
  // only value left - the earlier isometric PLAN mode (its own canvas,
  // terrain paint tool, placed objects) has been removed entirely. The
  // field itself stays (rather than being deleted outright) because the
  // project file format's own `kind` field is optional and additive
  // (ProjectSchema.ts) and this is still where its live value lives -
  // see project/ProjectManager.ts for how a legacy file saved with
  // `kind: "PLAN"` still loads, converted to SCHEMATIC with a message,
  // rather than being rejected.
  screenKind: ScreenKind;
  setScreenKind: (kind: ScreenKind) => void;

  // feat/help-system commit 1: which language the Help window's own
  // content shows in - see helpSlice.ts's own header for why this lives
  // in the project file (the only cross-reload persistence this app has)
  // rather than localStorage/sessionStorage (forbidden by this task's
  // GRANICE).
  helpLanguage: HelpLanguage;
  setHelpLanguage: (language: HelpLanguage) => void;

  // feat/device-form-from-canvas: which device's own configuration form
  // is currently requested open, if any - see DeviceFormRequest's own
  // comment (./types.ts) and deviceFormSlice.ts for the full reasoning.
  // App.tsx renders DeviceFormDialog (the SAME component Lista aparatow
  // itself uses) from this alone; every place an aparat is visible
  // calls openDeviceForm, never opens the dialog any other way.
  deviceFormRequest: DeviceFormRequest | null;
  openDeviceForm: (deviceId: string, sourceContext?: string) => void;
  closeDeviceForm: () => void;

  // fix/inline-device-creation commit 3: the parallel request for a
  // symbol that has NO device yet - see DeviceCreateOrAssignRequest's
  // own comment (./types.ts) for why this is a separate field rather
  // than a variant of deviceFormRequest above.
  deviceCreateOrAssignRequest: DeviceCreateOrAssignRequest | null;
  openDeviceCreateOrAssignForm: (symbolId: string, symbolType: string, sourceContext: string) => void;
  closeDeviceCreateOrAssignForm: () => void;
}
