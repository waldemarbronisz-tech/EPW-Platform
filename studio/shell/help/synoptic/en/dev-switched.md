# 4.4 SWITCHED - Controllable Two-State Devices

SWITCHED is a controllable two-state device: a contactor, a valve, a damper. It has feedback, a command output, supervision and a safe state.

## Feedback (feedback.mode)

DUAL mode uses two digital inputs (diClosed and diOpen), which distinguishes four states:

| diClosed | diOpen | Meaning |
| --- | --- | --- |
| 0 | 1 | Open |
| 1 | 0 | Closed |
| 0 | 0 | In motion, or a broken wire |
| 1 | 1 | Fault (both limit switches at once) |

SINGLE mode uses one input (diClosed) with optional negation (invert) and does NOT DISTINGUISH an intermediate state or a dead signal from OFF - that is a deliberate limitation of this mode, not a defect. NONE mode has no feedback input at all: control runs open-loop, the screen will never confirm the device's actual state.

## Command

The output count (1 or 2) and the style (MAINTAINED, PULSE or PULSE_TOGGLE) together describe the real circuit:

- 1 output, MAINTAINED - a typical contactor/valve with one coil held energized in the ON state.
- 1 output, PULSE - a short pulse on one coil, ON direction only (OFF is not commanded from here).
- 2 outputs, MAINTAINED - a typical three-position valve with separate OPEN/CLOSE coils.
- 2 outputs, PULSE - a typical bistable contactor with separate ON/OFF pulses (two coils).
- 1 or 2 outputs, PULSE_TOGGLE - a SINGLE-COIL impulse relay (R15/3P-class): every pulse toggles ON<->OFF, whichever output (or a local push-button) delivered it. The runtime pulses only when the feedback says the device is NOT already in the requested state - otherwise it would flip it the other way. Feedback (SINGLE or DUAL) is mandatory.

With 2 outputs, doOpen is required; with 1, it is forbidden. With PULSE and PULSE_TOGGLE, pulseMs (the pulse time in milliseconds, > 0) is required; with MAINTAINED, it is forbidden. PULSE_TOGGLE with feedback mode NONE is an error.

## Supervision and safe state

confirmTimeoutMs is the time (at least 100 ms - below that, supervision stops meaning anything against a real device's actual actuation time) allowed for feedback to confirm a state change before a discrepancy is reported (discrepancyAlarm) - a DISCREPANCY is a command that was sent but that feedback did not confirm within that time (a TIMEOUT is the same event named from the clock's side; discrepancyAlarm is whether to actually raise it as an alarm at all). safeState.onStartup and onLinkLoss (NO_CHANGE/OPEN/CLOSE) describe what THE HARDWARE ITSELF should do in those situations - see [1.3](help://synoptic/intro-principle).

> **Note:** switchCounter deliberately has NO warning-threshold field of its own in this contract - the threshold is defined in EPW-Logic-Studio, by reading the .COUNTER signal ([4.9](help://synoptic/dev-signals-commands)). A warning threshold baked into the hardware configuration would be hidden logic inside a hardware description - a deliberate design decision, not a missing feature.
