# Running a simulation and checking what the logic does

1. **Compile the project** (F5). Starting the simulation recompiles the
   project by itself, so that what runs is always the current logic, but
   it is worth seeing the errors sooner.
2. **Start** (F6, or the toolbar button) — the engine begins running
   scans in a loop, with the period the project settings specify.
3. **Force or toggle the inputs** in the property panel of a selected DI
   or internal bit input block, to simulate a signal from the hardware —
   see [Disabled blocks and forces](help:concept_disabled_blocks) for how
   forcing works.
4. **Watch the values on the canvas** — blocks and wires show their
   current state live while the simulation runs.
5. **Step / Step ×10** — run one scan or ten by hand, useful for
   following the logic step by step instead of at full speed; it works in
   the stopped state too (as a "step without writing outputs" — offline,
   touching no real hardware).
6. **Pause** — halts the run without resetting the state of stateful
   blocks (timers, counters, latches); Start resumes from the same place.
7. **Stop** (F7) — ends the simulation and resets block state to its
   initial values.

The Watched signals panel lets you pin any signals (physical, internal,
system) to a permanent view with a trend chart, independently of whatever
happens to be selected on the canvas.
