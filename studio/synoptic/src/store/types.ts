// Internal-audit fix (god-file breakup): the shape types that used to live
// at the top of the single 926-line store.ts, unchanged - moved here so
// every slice file (and store.ts itself) can import them without a
// circular value dependency. store.ts re-exports all of these from its own
// path, so none of the ~40 files elsewhere in src/ that already do
// `import type { SynopticObject } from '../store'` need to change.
import type { MeterRow } from '../symbols/scada/MeterSymbol';
import type { MeterElement } from '../meter/MeterElement';
import type { SignalPanelElement } from '../elements/SignalPanelElement';
import type { FrameElement } from '../elements/FrameElement';
import type { GroupCommandElement } from '../elements/GroupCommandElement';
import type { SetpointPanelElement } from '../elements/SetpointElement';

// chore/remove-isometric-plan-mode: SCHEMATIC is the only screen kind
// left - PLAN (the isometric mode) has been removed entirely (see
// project/ProjectManager.ts's own comment for how a legacy file with
// `kind: "PLAN"` still loads, converted). The type stays a union of one
// value, rather than being inlined as a bare string, so every existing
// call site (screenKind/setScreenKind, ProjectSchema.ts's own `kind`
// field) keeps its own explicit, self-documenting type unchanged.
export type ScreenKind = 'SCHEMATIC';

export interface SynopticObject {
  zIndex?: number;
  id: string;
  type: string;
  category: string;
  x: number;
  y: number;
  rotation: number;
  scaleX: number;
  scaleY: number;
  visible: boolean;
  locked: boolean;
  layer: number;

  // Properties
  designation?: string;
  name?: string;
  // feat/device-list-ui commit 5: which project-level device (src/
  // project/DeviceSchema.ts) this symbol represents - '' or undefined
  // means none, a perfectly valid state. The screen element never
  // stores anything about the device beyond its id: no config is ever
  // copied here, and the SAME device id may legitimately appear on any
  // number of objects/screens (this task's own core principle - see
  // DeviceBindingValidation.ts).
  deviceId?: string;
  tag: string;
  description: string;
  color: string;
  fill: string;
  border: string;
  text: string;
  font: string;
  fontSize: number;


  editor?: {
    preview_state?: string;
    preview_value?: string;
    unit?: string;
    format?: string;
  };

  // Runtime Bindings
  bindings?: {
    state?: { tag: string; data_type?: string };
    value?: { tag: string; data_type?: string };
    command?: { tag: string; data_type?: string; access?: 'WRITE' | 'READ_WRITE' };
    alarm?: { tag: string; data_type?: string };
    quality?: { tag: string; data_type?: string };
  };
  tooltip: string;

  // Layout
  width: number;
  height: number;

  customProperties: Record<string, string>;
  showDesignation?: boolean;
  showName?: boolean;
  labelPosition?: 'TOP' | 'BOTTOM' | 'LEFT' | 'RIGHT';
  labelOffsetX?: number;
  labelOffsetY?: number;

  // SCADA meter (scada.meter): rows are edited by hand for now - wiring
  // this to the device registry is a separate, later task. Optional: only
  // meter objects use it, every other object leaves it undefined.
  meterRows?: MeterRow[];

  // SCADA boundary point (scada.boundary_point): where a schematic
  // begins or ends (a utility feed, a well, a branch to a sub
  // installation). Optional: only boundary point objects use these three
  // - label/sublabel reuse the existing designation/description fields,
  // same convention as the label frame this symbol is built on. Every
  // other object leaves these undefined.
  boundaryDirection?: 'SOURCE' | 'SINK';
  boundaryMedium?: 'ELECTRICAL' | 'WATER' | 'VENTILATION';
  boundaryPortSide?: 'TOP' | 'BOTTOM' | 'LEFT' | 'RIGHT';
}

export interface CanvasState {
  zoom: number;
  panX: number;
  panY: number;
}

// feat/water-management commit 1: a point that landed EXACTLY on a
// symbol's terminal at the moment it was created remembers that
// terminal here, so it can follow the symbol through a move/rotate
// instead of being left behind (WireAnchoring.ts). Optional and
// additive - a connection saved before this field existed simply has
// no anchor on any of its points (free, exactly as it already
// behaved) - no schema version bump.
export interface WirePointAnchor {
  symbolId: string;
  terminalId: string;
}

export interface WirePoint {
  x: number;
  y: number;
  anchor?: WirePointAnchor;
}

// Node-based connection model (schema v2): a connection is a freehand
// orthogonal polyline, not a pair of ports. Two wires - or a wire and a
// symbol terminal - are joined simply by sharing a grid node; nothing
// else references anything by id. fromId/fromPort/toId/toPort are gone
// entirely - see NetResolver.ts for how wires and terminals are grouped
// into nets from geometry alone.
//
// feat/media-and-proportions part B: VENTILATION joins ELECTRICAL/WATER
// as a third medium value. This is a value added to the existing medium
// field, not a change to the connection's shape - schema version stays
// at 2 (see ProjectSchema.ts's CURRENT_SCHEMA_VERSION comment).
export interface SynopticConnection {
  id: string;
  points: WirePoint[]; // minimum 2, every point on a GRID_SIZE node, every segment horizontal or vertical
  medium: 'ELECTRICAL' | 'WATER' | 'VENTILATION';
  style: 'NORMAL' | 'BUS'; // BUS is a busbar/manifold: thicker, touchable anywhere along its length
  // feat/water-management commit 2: no longer set by hand in Properties
  // (that field is gone) and never read for drawing - NetResolver.ts's
  // own computed net state (ACTIVE/INACTIVE, from whether the net
  // touches an active source) decides the wire's color now. Left
  // optional, purely so a file saved before this commit (with a real
  // LIVE/DEAD value on every connection) still loads without error -
  // ProjectSchema.ts's own validator accepts an absent value too.
  state?: 'LIVE' | 'DEAD';
  // feat/wire-routing-around-obstacles commit 3, point (d): once a user
  // places their OWN bend on a wire (Alt+click insert), that wire is
  // "manual" from then on - the PRZELICZ TRASE command (WireRouter.ts's
  // own routeAround) skips it forever after, never silently reshaping a
  // route someone deliberately customized. Optional and additive
  // (absent = not manual, the default for every wire drawn before this
  // field existed, and for a wire never Alt+click-edited) - no schema
  // version bump, same convention as every other optional field above.
  isManualRoute?: boolean;
}

export interface Message {
  id: string;
  type: 'info' | 'error' | 'warning';
  text: string;
  time: string;
}

export interface HistorySnapshot {
  objects: SynopticObject[];
  connections: SynopticConnection[];
  meters: MeterElement[];
  signalPanels: SignalPanelElement[];
  frames: FrameElement[];
  // feat/control-elements commit 2: the group command button - optional
  // (added well after meters/signalPanels/frames became mandatory
  // fields here, so it follows the later, optional convention every
  // field added since then uses, rather than joining them as a
  // required one).
  groupCommands?: GroupCommandElement[];
  // feat/selector-symbol-setpoint-alarm: the setpoint panel - same
  // optional/additive treatment as groupCommands above.
  setpointPanels?: SetpointPanelElement[];
}

// feat/device-form-from-canvas: which device's configuration form is
// currently requested to be open, and why - the one piece of state
// every "aparat is visible here" entry point (a schematic symbol's own
// double-click, Properties' Aparat row, a meter/signal-panel row, a
// wizard row, Lista aparatow's own Edytuj) shares, via
// deviceFormSlice.ts's openDeviceForm/closeDeviceForm. Lives here, not
// in the slice file itself, for the same reason HistorySnapshot/Message
// above do: appState.ts imports shape types from this file, never from
// a sibling *Slice.ts (see appState.ts's own header comment on why).
export interface DeviceFormRequest {
  deviceId: string;
  // Shown in DeviceFormDialog's own header when present (task 3a) - e.g.
  // "Diagram, symbol -K1" - so the user knows where they opened the form
  // from. Left undefined for Lista aparatow's own Edytuj button: that
  // path's header stays exactly what it always was, unchanged.
  sourceContext?: string;
}

// fix/inline-device-creation commit 3: double-clicking a symbol that has
// NO device yet used to just post a Messages notice (feat/device-form-
// from-canvas commit 1) - it now opens DeviceFormDialog in its own
// "create or assign" mode instead, via openDeviceCreateOrAssignForm/
// closeDeviceCreateOrAssignForm (deviceFormSlice.ts). Kept as a SEPARATE
// field from DeviceFormRequest above, rather than folding both into one
// discriminated union: every existing caller of openDeviceForm/
// deviceFormRequest (Properties' Aparat row, meter/signal-panel rows,
// wizard rows, Lista aparatow's Edytuj, and this task's own device-form-
// from-canvas tests) keeps working completely unchanged, since it is
// still looking up an EXISTING deviceId - this is a genuinely different
// request shape (a symbol with no device yet, identified by the symbol
// itself, not a device id) rather than a variant of the same one.
export interface DeviceCreateOrAssignRequest {
  symbolId: string;
  // SynopticObject.type of the originating symbol - e.g.
  // 'electrical.disconnect_switch' - SymbolBehaviorMapping.ts's own
  // suggestBehaviorForSymbolType and DeviceCreationSuggestions.ts's own
  // suggestion functions are both keyed on this.
  symbolType: string;
  // Always present here (unlike DeviceFormRequest's own optional
  // sourceContext) - GRANICE requires the window's header to show where
  // it was opened from (screen name and symbol kind) for this flow,
  // there is no path that opens it without one.
  sourceContext: string;
}
