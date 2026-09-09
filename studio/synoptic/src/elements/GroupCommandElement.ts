// feat/control-elements commit 2 - the group command button: a screen
// element that issues the SAME command to every device in a
// user-configured list, e.g. "start all fans" or "all exterior lights
// off". Modeled by mirroring SignalPanelElement.ts's own pattern (its
// own header comment explains the convention this follows), not by
// inventing a new one.
//
// Deliberately NOT a symbol - no terminals, no fixed canvas, no entry
// in SymbolRegistry, its own store array (groupCommands), not
// `objects`.
//
// This is a screen-level CONVENIENCE, not new control logic: it only
// re-issues a command that already exists on every member device
// (SwitchedDevice's own .CLOSE/.OPEN, see DeviceSignals.ts) to several
// devices at once. It invents no new signal, no new command, and no
// interlock of its own - see this task's own GRANICE ("control logic
// belongs to EPW-Logic-Studio, never this editor").
//
// Pure, Konva-free (same convention as MeterElement.ts/
// SignalPanelElement.ts).

/**
 * A group command button. `command` is the single action every member
 * device receives when clicked - CLOSE or OPEN, the exact same two
 * values SwitchedDevice's own command already has (DeviceSchema.ts).
 * `deviceIds` deliberately holds bare device ids, not a copy of
 * anything about them - resolving which of those ids are still valid
 * SWITCHED devices is GroupCommandResolver.ts's job, at render time,
 * same as every other device-linked element in this project.
 */
export interface GroupCommandElement {
  id: string;
  x: number;
  y: number;
  width: number;    // user-set, clamped to [GROUP_COMMAND_MIN_WIDTH, GROUP_COMMAND_MAX_WIDTH]
  label: string;    // the button's own caption, e.g. 'Start wentylatorow' - freely editable, never derived from its members
  command: 'CLOSE' | 'OPEN';
  deviceIds: string[];
}

export const GROUP_COMMAND_MIN_WIDTH = 100;
export const GROUP_COMMAND_MAX_WIDTH = 300;
export const GROUP_COMMAND_DEFAULT_WIDTH = 160;
// Fixed - a button's height never depends on its content the way a
// panel's row count does, so unlike computeSignalPanelHeight there is
// nothing to derive; this is a plain constant, kept as a function
// anyway so every caller reads it the same way it reads the panel's
// own height (one convention, regardless of which element needs a
// constant vs. a real formula).
export const GROUP_COMMAND_HEIGHT = 36;

export function computeGroupCommandHeight(): number {
  return GROUP_COMMAND_HEIGHT;
}

/** Keeps a user-entered width inside the element's own [min, max] spec. */
export function clampGroupCommandWidth(width: number): number {
  return Math.min(GROUP_COMMAND_MAX_WIDTH, Math.max(GROUP_COMMAND_MIN_WIDTH, width));
}
