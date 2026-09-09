// EPW Device Registry - type contract shared across EPW-OS, EPW-Logic-Studio
// and this editor. This file defines DATA SHAPE ONLY - no validation logic
// (see DeviceValidation.ts) and no signal enumeration (see DeviceSignals.ts).
//
// Devices are classified by BEHAVIOR, not by device kind. There are exactly
// five behaviors. `kind` (e.g. 'contactor', 'valve') is a display label with
// no functional meaning - the behavior is what determines which fields,
// signals and commands a device has.

/** The five device behaviors. Nothing else exists, and nothing else may be added silently. */
export type DeviceBehavior = 'SWITCHED' | 'SIGNAL' | 'MEASURED' | 'MODULATED' | 'SELECTOR';

/**
 * Channel address, textual format: CARD.KIND.CHANNEL
 * e.g. 'ELA1.DI.12', 'ADA1.DO.4', 'ELA1.AI.3', 'ADA1.AO.1'
 * KIND is one of 'DI' | 'DO' | 'AI' | 'AO'. Validated in DeviceValidation.ts,
 * not encoded in the type system (it is user-entered text at authoring time).
 */
export type ChannelAddress = string;

export type ChannelKind = 'DI' | 'DO' | 'AI' | 'AO';

/** A physical/logical location (e.g. a switchgear panel or room). */
export interface LocationEntry {
  code: string;        // 'KOT' - A-Z and 0-9 only
  description: string; // 'Kotlownia'
}

/** A physical I/O card. Channels are numbered 1..channelCount. */
export interface CardEntry {
  id: string;                 // 'ELA1' - A-Z and 0-9 only
  model: string;               // 'ELA01' - descriptive label
  channelKind: ChannelKind;
  channelCount: number;        // e.g. 64
}

/** Fields common to every device, regardless of behavior. */
export interface DeviceCommon {
  id: string;             // 'KOT_KMG1' - machine key, immutable
  designation: string;    // '-K1' - designation shown on the diagram
  name: string;            // 'Stycznik grzalki' - human-readable description
  behavior: DeviceBehavior;
  kind: string;             // 'contactor' - label: icon + description, no functional meaning
  publishToHa: boolean;    // whether to publish an entity to Home Assistant
}

/** SWITCHED: controllable two-state device (contactor, valve, damper...). */
export interface SwitchedDevice extends DeviceCommon {
  behavior: 'SWITCHED';
  feedback: {
    mode: 'DUAL' | 'SINGLE' | 'NONE';
    diClosed?: ChannelAddress; // required for DUAL and SINGLE
    diOpen?: ChannelAddress;   // required for DUAL, forbidden for SINGLE and NONE
    invert?: boolean;          // allowed only for SINGLE
  };
  extraInputs?: {
    diFault?: ChannelAddress;  // optional, protection-trip contact
  };
  command: {
    outputCount: 1 | 2;
    style: 'MAINTAINED' | 'PULSE';
    doClose: ChannelAddress;   // always required
    doOpen?: ChannelAddress;   // required for outputCount 2, forbidden for 1
    pulseMs?: number;          // required for PULSE, forbidden for MAINTAINED
  };
  supervision: {
    confirmTimeoutMs: number;
    discrepancyAlarm: boolean;
  };
  safeState: {
    onStartup: 'NO_CHANGE' | 'OPEN' | 'CLOSE';
    onLinkLoss: 'NO_CHANGE' | 'OPEN' | 'CLOSE';
  };
  // Whether to count switching operations. Deliberately has NO warning-threshold
  // field: a threshold is control logic, defined in EPW-Logic-Studio by reading
  // the .COUNTER signal. A threshold baked into the device config would be
  // hidden logic inside a hardware description. Do not add one, ever.
  switchCounter: boolean;
  // Pure documentation of what an INHIBIT_CLOSE/INHIBIT_OPEN condition
  // means for this device, e.g. "Zablokowane, gdy drzwi rozdzielnicy sa
  // otwarte". The actual inhibit VALUE is live runtime logic written by
  // EPW-Logic-Studio (see DeviceSignals.ts's own header comment on why) -
  // this field never wires to anything and is never read by any command
  // path. It exists so an engineer reading the device form or the
  // diagram can see WHY a command might be refused, without that reason
  // being hidden logic baked into the hardware description. Optional:
  // most devices have no interlock at all.
  interlock?: {
    closeDescription?: string; // shown next to .INHIBIT_CLOSE
    openDescription?: string;  // shown next to .INHIBIT_OPEN
  };
}

/**
 * SELECTOR: a physical multi-position selector switch (Hand-Off-Auto,
 * Local-Remote, a multi-speed selector...). Deliberately READ-ONLY, with
 * no command of any kind - a real selector switch is turned by hand at
 * the panel, not driven remotely, so there is nothing for logic or an
 * operator to command here, unlike SWITCHED. `positions` must have at
 * least two entries; each position's own `feedback` is optional (some
 * installations only wire a contact for the non-default positions and
 * infer the rest), but at most one position may be selected at a time -
 * that is a runtime fact this editor cannot check without live data.
 */
export interface SelectorDevice extends DeviceCommon {
  behavior: 'SELECTOR';
  positions: SelectorPosition[];
}

export interface SelectorPosition {
  name: string;               // 'RECZNIE', '0', 'AUTOMAT' - shown to the operator, exactly as typed
  feedback?: ChannelAddress;  // DI that reads true when this position is selected
}

/** SIGNAL: read-only signalling input (a lamp/status contact, not controllable). */
export interface SignalDevice extends DeviceCommon {
  behavior: 'SIGNAL';
  feedback: {
    di: ChannelAddress;
    invert: boolean;
  };
  alarmState: 'HIGH' | 'LOW'; // which level counts as alarm
  debounceMs: number;          // anti-chatter delay
}

/** MEASURED: analog measurement input. */
export interface MeasuredDevice extends DeviceCommon {
  behavior: 'MEASURED';
  input: ChannelAddress; // must be an AI channel
  unit: string;           // '°C'
  rangeMin: number;
  rangeMax: number;
  format: string;         // '0.0'
  deadband: number;       // dead-band around the value
}

/**
 * MODULATED: continuously controllable device (e.g. a modulating valve/VFD).
 * Not wired into the UI yet, but must exist in the type contract from day
 * one - adding it later would mean a schema version bump and migrations
 * across all three applications.
 */
export interface ModulatedDevice extends DeviceCommon {
  behavior: 'MODULATED';
  setpointOutput: ChannelAddress;  // must be an AO channel
  feedbackInput?: ChannelAddress;  // optional, must be an AI channel
  unit: string;
  rangeMin: number;
  rangeMax: number;
  startupValue: number;
  safeValue: number;
}

export type Device = SwitchedDevice | SignalDevice | MeasuredDevice | ModulatedDevice | SelectorDevice;

/** The device list container: locations, cards and devices. */
export interface DeviceRegistry {
  locations: LocationEntry[];
  cards: CardEntry[];
  devices: Device[];
}
