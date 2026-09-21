// Internal-audit fix (god-file breakup): the combined store shape, moved
// out of store.ts unchanged so every slice creator (objectsSlice.ts,
// selectionSlice.ts, etc.) can type itself as
// `StateCreator<AppState, [], [], ItsOwnSlice>` - Zustand's own
// documented "slices" pattern - without a circular VALUE import back to
// store.ts (this file has no runtime code in it at all, only the type).
import type { RuntimeViewport } from '../project/RuntimeViewport';
import type { SelectionIds, WorkMode } from '../project/WorkModes';
import type { MeterElement } from '../meter/MeterElement';
import type { SignalPanelElement } from '../elements/SignalPanelElement';
import type { FrameElement } from '../elements/FrameElement';
import type { WallElement } from '../elements/WallElement';
import type { CircuitBinding } from '../project/CircuitBindings';
import type { ScreenContent, ScreenInfo } from '../project/ScreenContent';
import type { WallMaterialId, FloorMaterialId } from '../theme/Materials';
import type { GroupCommandElement } from '../elements/GroupCommandElement';
import type { SetpointPanelElement } from '../elements/SetpointElement';
import type { ChannelKind, Device, LocationEntry, CardEntry } from '../project/DeviceSchema';
import type { CanvasState, DeviceCreateOrAssignRequest, DeviceFormRequest, HistorySnapshot, Message, ScreenKind, SynopticConnection, SynopticObject } from './types';
import type { HelpLanguage } from '../i18n/HelpLanguage';
import type { WorkspaceLayout, TileFrame } from '../project/WorkspaceLayout';
import type { CommandRequest } from '../project/CommandRequest';
import type { SimulationEvent } from './simulationSlice';
import type { RoomElement } from '../elements/RoomElement';

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
    // feat/room-plan: which material the derived room floors are
    // painted with. Screen-level, not per-room: rooms are derived from
    // walls (RoomFloors.ts), so they have no identity of their own to
    // hang a setting on. Optional and additive - absent means
    // DEFAULT_FLOOR_MATERIAL.
    floorMaterial?: FloorMaterialId;
    // The part of the plan the panel shows (project/RuntimeViewport.ts);
    // absent = the panel fits everything drawn. Per screen, like
    // floorMaterial: parked in ScreenContent when the screen is not live.
    viewport?: RuntimeViewport;
  };
  // The editor canvas's own size on screen (Canvas.tsx's ResizeObserver),
  // so View -> "Runtime frame: what I see now" can turn the current
  // zoom/pan into a canvas rectangle. Session state, never saved.
  canvasViewportSize: { width: number; height: number };
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
  // feat/room-plan: the wall element - a straight architectural wall
  // segment. Its own array, like the frame, for the same reason: it
  // is not a symbol (see elements/WallElement.ts).
  walls: WallElement[];
  // ZADANIA p. 6: the room records the walls point at (elements/RoomElement.ts).
  rooms: RoomElement[];
  // feat/room-plan: which device switches each circuit - the link
  // between the plan and the controller (project/CircuitBindings.ts).
  // Project-level, not per fixture: a circuit has one device, and a
  // copy on every fixture would drift the moment one was edited.
  circuits: CircuitBinding[];
  // feat/multi-screen: one controller runs more than one room, so a
  // project holds several screens and switches between them. The ACTIVE
  // screen's content is the ordinary objects/walls/... arrays above -
  // only the others live in screenContents. See project/ScreenContent.ts
  // for why it is split that way.
  screens: ScreenInfo[];
  activeScreenId: string;
  screenContents: Record<string, ScreenContent>;
  addScreen: (name?: string) => void;
  // feat/workspace: every screen on show as a tiled window, the one you
  // work in being the active one. See store/workspaceSlice.ts. Session-
  // only UI state: it says how you are looking at the project, not what
  // the project is, so none of it is ever serialized.
  workspaceLayout: WorkspaceLayout;
  /** Screens the user took off the workspace. New screens are shown by default. */
  hiddenScreens: string[];
  /** Each screen's own zoom and pan, so switching tiles never resets a view. */
  screenViews: Record<string, CanvasState>;
  /** Each screen's own undo stack, so clicking between tiles never empties it. */
  screenHistories: Record<string, { history: HistorySnapshot[]; historyIndex: number }>;
  /** feat/live-view: the controller's tag values Studio pushes in while "Na żywo" is on (null = off), and the per-object states derived from them - see store/liveSlice.ts. */
  liveValues: Record<string, unknown> | null;
  liveStates: Record<string, string>;
  setLiveValues: (values: Record<string, unknown> | null) => void;
  /** feat/window-snapping: where each tile sits in the `free` arrangement, as fractions of the area. Session state like the rest. */
  tileFrames: Record<string, TileFrame>;
  setWorkspaceLayout: (layout: WorkspaceLayout) => void;
  showScreen: (screenId: string) => void;
  hideScreen: (screenId: string) => void;
  /** One tile moved or snapped by hand. */
  setTileFrame: (screenId: string, frame: TileFrame) => void;
  /** Leaves the automatic arrangement: every shown tile keeps the place it has right now, and from here the user places them. */
  arrangeFreely: (frames: Record<string, TileFrame>) => void;

  // feat/workspace: simulation - the plan operated the way the
  // controller will operate it, through a confirmation window rather
  // than by a bare click (store/simulationSlice.ts). Session-only, and
  // deliberately non-destructive: stopping restores every state the
  // simulation changed.
  simulationRunning: boolean;
  commandRequest: CommandRequest | null;
  /** Circuits whose command has gone out and whose feedback contact has not answered yet. Only ever non-empty for a device that HAS feedback. */
  pendingCircuits: string[];
  simulationLog: SimulationEvent[];
  startSimulation: () => void;
  stopSimulation: () => void;
  /** A click on a fixture: an immediate toggle while editing, a command window while simulating. The one entry point every view calls. */
  operateAt: (objectId: string) => void;
  confirmCommand: () => void;
  cancelCommand: () => void;
  clearSimulationLog: () => void;
  renameScreen: (id: string, name: string) => void;
  deleteScreen: (id: string) => void;
  switchScreen: (id: string) => void;
  /** Flush the live arrays into screenContents. Anything reading ALL screens - saving above all - must call this first. */
  captureActiveScreen: () => void;
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
  selectedWallIds: string[];
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
  /** Walls copied with the rest of a selection, so a room copies as a room. */
  clipboardWalls: WallElement[];
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
  updateCard: (id: string, kind: ChannelKind, entry: CardEntry) => void;
  deleteCard: (id: string, kind: ChannelKind) => void;
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
  // feat/room-plan: the wall tool. Armed from the toolbar; each click
  // on the canvas drops one wall and starts the next at its end, so a
  // room is drawn as a chain rather than as separate drags.
  isDrawingWall: boolean;
  isDrawingRoom: boolean;
  wallDrawThickness: number;
  wallDrawHeight: number;
  wallDrawMaterial: WallMaterialId;
  setDrawingWallMode: (active: boolean) => void;
  setDrawingRoomMode: (active: boolean) => void;
  setWallDrawThickness: (thickness: number) => void;
  setWallDrawHeight: (height: number) => void;
  setWallDrawMaterial: (material: WallMaterialId) => void;
  setFloorMaterial: (material: FloorMaterialId) => void;
  // feat/room-plan: Podglad mode. In it a click OPERATES the drawing
  // (toggles the circuit under the cursor) instead of selecting it -
  // see project/CircuitResolver.ts. Session-only UI state, never
  // serialized, exactly like the drawing tools above.
  // feat/room-lighting: the false-colour illuminance map over the
  // working plane. A VIEW state like previewMode - never serialized,
  // since it says how you are looking at the plan, not what it is.
  // feat/text-formatting: the text box currently open for typing on the
  // canvas (TextEditOverlay), or null. Session-only.
  editingTextId: string | null;
  setEditingTextId: (id: string | null) => void;
  /** The format the format bar holds while no text is selected - what the next text box is created with, as in a word processor. */
  nextTextFormat: Partial<SynopticObject>;
  setNextTextFormat: (updates: Partial<SynopticObject>) => void;
  showIlluminance: boolean;
  setShowIlluminance: (active: boolean) => void;
  previewMode: boolean;
  /** feat/synoptic-modes: what a click can reach - SYMBOLS, ROOMS, CONNECTIONS or ANNOTATIONS (project/WorkModes.ts). Session state, never saved. */
  workMode: WorkMode;
  setWorkMode: (mode: WorkMode) => void;
  setPreviewMode: (active: boolean) => void;
  toggleCircuitAt: (objectId: string) => void;
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
  // Task "Studio: wyostrzenie stylu" Problem 4.3 - canvasConfig.background
  // is already a project-file field (serialized like every other
  // canvasConfig value, ProjectSchema.ts), but nothing ever WROTE to it
  // before this task - checked empirically, not assumed (no existing
  // setter, no UI reachable it from at all). One setter, following the
  // exact shape every other project-field setter here already has.
  setCanvasBackground: (color: string) => void;
  setRuntimeViewport: (viewport: RuntimeViewport | undefined) => void;
  setCanvasViewportSize: (size: { width: number; height: number }) => void;
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
  addWall: (wall: Omit<WallElement, 'id'>) => void;
  updateWall: (id: string, updates: Partial<WallElement>) => void;
  updateWalls: (updates: { id: string; updates: Partial<WallElement> }[]) => void;
  // feat/room-plan: copy one wall's thickness/height/material onto
  // every wall joined to it. Editing a wall usually means editing the
  // ROOM - you pick OSB for the workshop, not for its north wall -
  // and doing that one wall at a time is four identical edits that
  // also leave the room un-mitred in between.
  applyWallStyleToRoom: (wallId: string) => void;
  // feat/room-plan: four walls round a rectangle, in ONE action and ONE
  // history entry. Drawing a plain rectangular room corner by corner is
  // the commonest thing this tool is used for, and doing it as four
  // separate walls is four chances to miss a corner by a pixel - which
  // is also four chances to end up with a room that does not close and
  // therefore gets no floor.
  addRoomWalls: (rect: { x: number; y: number; width: number; height: number }) => void;
  updateRoom: (id: string, updates: Partial<RoomElement>) => void;
  /** The record for these walls - created and stamped on the whole wall chain when missing. Returns its id. */
  assignRoomToWalls: (wallIds: string[]) => string;
  // feat/cad-marquee: resize the whole selection - a room selected with
  // a crossing marquee, above all. Geometry scales, objects move; see
  // project/GroupScale.ts. Writes no history entry of its own, so a drag
  // can call it on every frame and record ONE entry when it ends.
  /** The walls/objects at the start of a handle drag; scaleSelection maps from these (see elementsSlice). */
  scaleOrigin: { walls: WallElement[]; objects: SynopticObject[] } | null;
  beginScaleSelection: () => void;
  endScaleSelection: () => void;
  scaleSelection: (
    before: { x: number; y: number; width: number; height: number },
    after: { x: number; y: number; width: number; height: number },
    snapStep?: number
  ) => void;
  /** Bind (or, with an empty id, unbind) the device that switches one circuit. */
  setCircuitDevice: (circuit: string, deviceId: string | undefined) => void;
  addFrame: (frame: Omit<FrameElement, 'id'>) => void;
  updateFrame: (id: string, updates: Partial<FrameElement>) => void;
  addGroupCommand: (el: Omit<GroupCommandElement, 'id'>) => void;
  updateGroupCommand: (id: string, updates: Partial<GroupCommandElement>) => void;
  addSetpointPanel: (panel: Omit<SetpointPanelElement, 'id'>) => void;
  updateSetpointPanel: (id: string, updates: Partial<SetpointPanelElement>) => void;
  deleteObjects: (ids: string[], connIds?: string[], meterIds?: string[], signalPanelIds?: string[], frameIds?: string[], groupCommandIds?: string[], setpointPanelIds?: string[], wallIds?: string[]) => void;
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
  selectWalls: (ids: string[], multi?: boolean) => void;
  selectGroupCommands: (ids: string[], multi?: boolean) => void;
  selectSetpointPanels: (ids: string[], multi?: boolean) => void;
  // commit 3 (feat/editing-and-signal-panel), extended in commit 2
  // (feat/appearance-selection-frames) with a fifth kind, in
  // feat/control-elements commit 2 with a sixth, and in
  // feat/selector-symbol-setpoint-alarm with a seventh: replaces the
  // whole selection with a mix of all seven kinds at once (the
  // rubber-band's own result) - and Ctrl+A's "select everything on screen".
  selectMixed: (selection: { objectIds?: string[]; connectionIds?: string[]; meterIds?: string[]; signalPanelIds?: string[]; frameIds?: string[]; groupCommandIds?: string[]; setpointPanelIds?: string[]; wallIds?: string[] }) => void;
  selectAll: () => void;
  clearSelection: () => void;
  // Arrow keys (commit 3): every selected object/meter/signalPanel/
  // frame/connection moves by (dx, dy) together, as one history entry
  // per keypress.
  moveSelectionBy: (dx: number, dy: number) => void;
  /** Moves exactly these elements (walls included) - a room with its contents. One history entry unless saveHistory is false (a live drag saves once at the end). */
  moveElementsBy: (selection: SelectionIds, dx: number, dy: number, saveHistory?: boolean) => void;

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

  // feat/library-recent-and-search: the symbols most recently placed,
  // newest first, so the library can offer them before anything else -
  // the same list the Logic editor's own library has always kept. Never
  // part of a project file: it describes the person drawing, not the
  // drawing. See project/RecentSymbols.ts.
  recentSymbols: string[];
  recordSymbolUse: (type: string) => void;

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
