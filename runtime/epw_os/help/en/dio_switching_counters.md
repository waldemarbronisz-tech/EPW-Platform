# Switching counter (mechanical device lifespan)

Switching devices (breakers, contactors) have a rated mechanical
lifespan — the manufacturer specifies how many switching cycles a
device can take before it needs service or replacement. The program
counts this automatically from digital input state changes — nothing
extra needs to be wired or measured.

## What is counted

For each digital input (DI), separately:

- **Closes** — the number of OFF-to-ON transitions,
- **Opens** — the number of ON-to-OFF transitions,
- **Total time closed** — the cumulative time the input has spent ON,
  counted from the first startup (or from the last counter reset),
- **Date and time of the first and last recorded transition**.

The very first state reading after the program starts is not counted
as a transition — only a real, subsequent state change is.

## Where this shows up

- **Digital Inputs** — Closes, Opens, and Closed Time columns, one row
  pair for each of the 64 inputs.
- **Main View** — the device window (click a breaker/contactor on the
  diagram) shows a short summary; the **Properties** button in that
  window shows the full detail, including the first and last
  transition timestamps.

## Data persistence

Counters are saved to the project file and survive a program restart -
nothing needs to be re-started manually. Saving to disk does not happen
on every state change (that would slow down processing) - the program
buffers the counters in memory and saves them periodically, and always
when the program shuts down.

## Resetting a counter

After physically replacing a device, reset its counter to track the
NEW device's wear from zero. To reset:

1. Right-click the Closes, Opens, or Closed Time column in the Digital
   Inputs table.
2. Choose **Reset Switching Counter...**.
3. Confirm - this cannot be undone.

Requires **Engineer** level and works in any operating mode (not just
simulation - this is a maintenance tool, used on real hardware). Every
reset is recorded to the [audit log](help://ea_audit_log), not just the
operational Event Recorder.

## Warning threshold (optional)

Each input can have its own threshold - a number of closes above which
the program shows a warning (the Closes column changes color in the
table, and the device window on Main View shows an extra message). No
threshold is set by default - the feature is fully optional, per
device.

Setting a threshold uses the same right-click menu as resetting -
**Set Warning Threshold...** (also Engineer-only).
