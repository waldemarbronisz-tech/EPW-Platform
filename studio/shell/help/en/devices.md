# Device Composition

Which **modules** this controller is made of. Not cards — functions.

A tick decides two things at once:

- **in Studio** — whether that module's branch appears in the tree at
  all;
- **on the controller** — whether the module is constructed. A module
  outside the composition has no object, no thread and no tags. It is
  not "disabled" — it is not there.

## Columns

**Name**, **Description**, **Active** (YES/NO — click to toggle).

## The modules

| Module | What it brings |
|---|---|
| Intrusion Alarm | zones, supervised lines, arming |
| Electrical Protection | ANSI settings executed by the ADA01 |
| Process Protection | thresholds on analog points |
| Trends | value history (the Historian) |
| Power Quality | mains parameters: voltage, THD, imbalance |
| Bus Diagnostics | frame and error counters |
| System Topology | a view of what the installation really consists of |
| Engineer Mode | extra verification tools at Engineer level |
| Analog Inputs | whether the controller handles AI points at all |
| Switching Counters | operation counts and running time for apparatus |
| Service Notes | the technician's logbook on points |
| Alarm History | the intrusion alarm's own event log |
| Alarm Live View | a live view of zones and lines on the panel |

## Disabling never deletes data

If a module already has data in the project, Studio says so outright:
the branch disappears from the tree, but **the data stays**. Re-enabling
brings it all back. The same on the controller.

A module with data but outside the composition is reported by [Check
Project](help://validation) as a warning — not an error.
