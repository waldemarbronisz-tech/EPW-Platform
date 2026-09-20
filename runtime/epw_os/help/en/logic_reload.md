# Reloading the Logic Program

**Project → Reload logic program...**, Engineer level, audited.

It re-reads the logic from the project file on disk and puts it into the
scan, **without restarting the controller**.

## What actually happens

1. The running scan is **stopped**, which drives every output it
   controls to its safe state (digital off, analog 0).
2. The new program is read and checked.
3. The scan starts again on it.

Between steps 1 and 3 the interlocks in that program are not protecting
anything. That is why the panel asks first rather than just doing it —
interrupting live interlocks has to be your decision, not a surprise.

## What it does not do

**Only the program.** Cards, points, apparatus, screens and the alarm
system are not re-read by this command. To put a whole new project into
service, use **File → Open** — see [Installing a
Project](help://proj_install), which rebuilds all of that in place and
reloads the logic as its last step.

## If the new program is refused

The controller says so, with the reason, and is then left **without user
logic** rather than with a program half in service. The previous program
is not resurrected: it was stopped in step 1, and silently going back to
it would mean the panel showed one thing and the plant did another.

Recompile in Logic Studio, install the project again, and reload.
