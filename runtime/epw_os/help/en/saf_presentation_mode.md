# Presentation Mode

Runs a prepared demonstration scenario - value changes, commands, and
alarms, on a fixed schedule - so the system can be shown in a few
minutes without narrating or clicking through it manually. Tools >
Presentation Mode... Engineer level.

## Requires Training Mode

Presentation Mode **cannot start while [Training Mode](help://saf_training_mode)
is off** - this is a hard requirement, not a preference. If Training
Mode isn't already active when you click Start, the dialog asks whether
to enable it; it never turns it on by itself. This is what keeps a
scripted demo from ever reaching real hardware - the same driver-layer
cutoff Training Mode already provides.

## Scenarios

A scenario is a file (`epw_os/presentation_scenarios/*.json`), not
something built into the program - a list of timed steps, each one a
tag value change, a command (going through the exact same validation a
real Force button would - a scenario can't skip a permission or
interlock check), an alarm being raised or cleared, a device
temporarily going silent on the bus, or a switching-counter warning
threshold being temporarily lowered for a short demo. Pick one from
the dropdown before clicking Start - its description is shown right
there so you know what you're about to run. EPW OS ships with six:

- **Voltage Sag and Protective Trip** - normal operation, a voltage
  sag, an undervoltage alarm, a protective trip, and recovery.
- **Normal Operation and Manual Control** - the simplest: a device
  closes and opens on command, with real feedback confirmation.
- **Communication Loss and the Fault Latch** - a device stops
  answering; the real 3-missed-cycle detection fires; the fault latch
  survives communication returning and requires manual acknowledgement.
- **Overload and Rising Current** - current climbs gradually (visible
  on the Trends page), crosses a warning then a trip threshold, an
  alarm fires, the breaker opens.
- **Command Sent, Never Confirmed** - a command is sent but its
  feedback never arrives; the real command-supervision timeout fires
  and the device is never shown as closed.
- **Mechanical Wear and Switching Counters** - a series of switching
  cycles crosses a (temporarily lowered) counter warning threshold.

See `epw_os/presentation_scenarios/README.md` for the file format if
you want to write your own.

## Controls

- **Start** - runs the selected scenario from its first step.
- **Pause / Resume** - the countdown to the next step stops and later
  resumes from exactly where it left off.
- **Step Forward** - executes the next step immediately, without
  waiting for its scheduled time.
- **Stop** - ends the scenario and puts back every value it changed
  (tag values, and switching-counter records including a temporarily-
  lowered warning threshold), restoring the state the system was in
  right before Start. A scenario that runs to the end on its own does
  the same thing automatically - you don't need to click Stop just to
  clean up. The one deliberate exception: a real SafetyKernel fault
  latch (see [System Health Monitoring](help://saf_kernel)) a scenario
  lets happen is never reverted by Stop, or by anything else other
  than a genuine, manual acknowledgement on the Alarms page - see
  "Communication Loss and the Fault Latch" above.

## The indicator

A status-bar badge separate from Training Mode's own indicator shows
while a presentation is running - the two are independent signals
(you'll normally see both at once, since Presentation Mode requires
Training Mode), not one standing in for the other.

## Audit trail

Starting and stopping a presentation are both recorded to the
[Audit Log](help://ea_audit_log), same as any other security-relevant
action.
