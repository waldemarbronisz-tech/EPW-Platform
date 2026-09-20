# Electrical Protection

The settings of ANSI relay functions. **The ADA01 card executes them**,
not the controller's program — here you set the values it works with.

On the left a tree: category → function → stage. On the right the
selected stage's configuration.

## Categories and functions

| Category | Functions |
|---|---|
| **Voltage** | 27 under voltage, 59 over voltage, 59N neutral overvoltage, 47 phase sequence / phase loss |
| **Frequency** | 81U under frequency, 81O over frequency |
| **Current** | 50 instantaneous overcurrent, 51 time overcurrent, 46 negative sequence, 49 thermal overload, 50N/51N earth fault |
| **Power supply** | control voltage loss, technical supply loss |

Most functions have **two stages** — usually the first as a warning, the
second as a trip.

## A stage's fields

| Field | Meaning |
|---|---|
| **Enabled** | whether the stage runs at all |
| **Quantity** | what is measured (voltage, current, frequency…) — from the catalogue |
| **Setting** | the pickup threshold, in the function's unit |
| **Hysteresis** | how far it must come back before it stops being exceeded |
| **Delay** | how long the excursion must last before the stage acts (ms) |
| **Action** | `Warning` or `Trip` |

## Where the initial values come from

From the ADA01 catalogue. **A stage the project does not mention has the
catalogue's default** — a missing entry does not mean "disabled", it
means "default". After sending the project it is worth comparing them
with reality through **Controller Settings (live)** in [Controller
Connection](help://controller).

Stage values are **settings**, not structure: the panel may change them
(with an audit entry) and Studio will see the difference — see [Saving,
revisions and settings](help://save_versioning).
