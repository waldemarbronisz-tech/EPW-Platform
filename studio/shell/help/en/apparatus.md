# Apparatus Registry

An apparatus is a thing the operator handles as a whole: a breaker, a
contactor, a valve, a drive. The registry ties it to raw points.

| Column | Meaning |
|---|---|
| **Id** | its designation, unique (e.g. `Q1`, `KM1`) |
| **Behavior** | `SWITCHED`, `SIGNAL`, `MEASURED`, `MODULATED`, `SELECTOR` |
| **Kind** | the catalogue type — breaker, contactor, valve… |
| **Feedback** | the points you read the state from; the button opens the list |
| **Command** | the output points; assigned the same way |
| **Command style** | what the pulse looks like — see below |
| **Pulse** | pulse length in ms (for the pulsing styles) |

## Command styles

**MAINTAINED (level)** — energized = ON (one coil), or one coil per
direction held energized.

**PULSE (a pulse per direction)** — separate coils, a pulse for each
direction. An "on" state exists only when there is a single output.

**PULSE_TOGGLE (single-coil impulse relay)** — **one** R15/3P-class coil
behind one or two outputs. Every pulse **toggles**, so the runtime
pulses only when the feedback says the apparatus is not already in the
requested state. **Feedback is mandatory here** — without knowing the
current state every pulse would be a guess.

## What [Check Project](help://validation) looks for

- an apparatus pointing at a point that is not in the registry;
- an apparatus pointing at a point on a card no longer in the
  composition;
- **a point assigned to two apparatus at once**;
- a pulsing style with a pulse time of 0;
- `PULSE_TOGGLE` with no feedback, or with more than two outputs.

## Where the apparatus turns up later

- on the [screen](help://screens) — a symbol bound by `deviceId`;
- in the [logic](help://logic) — as one command, not two outputs;
- in [Protection Tests](help://protection_tests) — as a subject whose
  feedback time can be measured.
