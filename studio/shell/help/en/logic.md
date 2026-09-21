# Logic

The logic editor's full description — concepts (labels, markers, the
scan cycle), guides, a page for every block and the shortcuts — is in
this same help, under [Logic — the logic editor](help://logic/welcome);
F1 on a selected block opens its catalog page.

The control-logic editor (Logic Studio) as a Studio department — the
block library, simulation, compilation and export to the controller: the
same tools as the standalone Logic Studio, in one skin with every other
department.

## What you program on

On **this project's addresses**: `ELA1.DI.1`, `ADA1.DO.3`, analog points
with their engineering range and unit. Cards and points are bridged into
the editor automatically — you do not enter them a second time.

Besides those you have:

- **internal bits** (`M.`) and **retentive bits** (`MR.` / `MWR.`) that
  survive a controller restart;
- **system signals `SYS.*`** — controller state, access level,
  communications, pulse and blink generators;
- **alarm signals `SSWIN.*`** — armed, alarm, alarm memory, tamper,
  readiness, and the sounder and its commands.

## The sounder: you are the one who wires it

The controller **drives no siren**. It publishes state —
`SSWIN.SIREN_ACTIVE` (it should be sounding), `SIREN_TIME_LEFT`,
`STROBE_ACTIVE` (the light), `PANIC` — and which output a siren hangs
on, through which interlocks, is a line of the diagram you draw here.
The settings (how long it may sound, whether a hold-up line stays
silent) are in [Zones](help://zones).

Likewise `SSWIN.CMD_SILENCE` — stopping the noise without touching the
alarm.

## Compiling and exporting

The logic travels to the controller **compiled, inside the project
file**. Saving the project takes the current compilation result; if the
diagram does not compile, Studio says so outright and **keeps the
previously compiled version** — the controller never receives a
half-finished program.

After sending you can check that the scan really runs: [Controller
Connection](help://controller) shows the block count, the cycle time,
the number of scans and how many outputs the logic drives.

## The editor's own help

Logic Studio has **its own, full help section**: concepts (labels versus
markers, the one-scan delay, analog signal quality, macros), step-by-step
guides, and a **block catalogue** generated from the live library —
every block with its pins, properties and defaults. Open it from inside
the editor; **F1 on a selected block** goes straight to its description.
