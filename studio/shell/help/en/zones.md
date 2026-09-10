# Zones

A zone is a named group of supervised lines, armed/disarmed as one
unit, with its own **exit delay** and **entry delay** (in seconds) —
real fields from the runtime's intrusion alarm module.

The **Power Supervision** section (at the bottom) is system-wide, not
per-zone: one analog point for mains (230V), a separate one for the
battery, each with its own "OK state = high" (which signal level means
healthy).

A zone with lines still assigned cannot be removed — reassign or
remove its lines in "Supervised Lines" first.
