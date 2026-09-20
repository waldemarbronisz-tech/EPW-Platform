# What the Logic Program Is

This controller does not only display and record — it **runs a control
program**. The program is a block diagram built in Logic Studio,
compiled there and carried inside `projekt.epw`. There is no separate
file to install.

## The scan

The program runs in a loop, on its own thread: read every input it uses,
evaluate every block, write every output it drives. One pass is a
**scan**. The status bar shows how long a scan takes — see
[The Logic Indicator](help://logic_state).

A block's output can only be seen by the next block in the same scan if
the compiler could order them that way; where a loop makes that
impossible, the value arrives **one scan later**. That is not a fault —
it is how every cyclic controller works, and Logic Studio says which
connections it applies to.

## What it is allowed to drive

Outputs, and only through the driver layer — the same boundary a command
from this panel goes through. That means the safety kernel, a
[force](help://dio_force) held on that output and
[Training Mode](help://saf_training_mode) all apply to logic exactly as
they apply to you.

An output driven by logic is **interlocked against manual operation**:
the panel refuses to command it, and says why, rather than fighting the
program for it scan after scan. Letting the command through would put
you and the scan in a race you always lose — the next scan overwrites
it a few milliseconds later, which looks exactly like a command that
"did not work".

The interlock only applies **while the scan is running**. A stopped
program drives nothing, so manual control is then the only control there
is, and the panel allows it.

## One case where everything is blocked

If this controller was configured to run a logic program and that
program could not be loaded, commands are refused with **"Logic Runtime
Unavailable - Commands Blocked (Fail Safe)"**. That is not a broken
panel: the controller cannot tell which interlocks should be protecting
the plant, so it does not let anything be operated until it can. A
controller that was never given logic at all is unaffected — it has
nothing to be unsure about.

## When the program stops

Stopping the scan drives every output the program controls to its **safe
state** — digital off, analog 0 — and leaves it there. That is
deliberate: a half-evaluated program controlling a plant is worse than
no program at all.

This happens when the scan is stopped, when the logic is
[reloaded](help://logic_reload), and while the whole project is being
[reinstalled](help://proj_install).

## If the program was refused

A program the controller cannot load is reported at startup and the
controller **runs without user logic** — it does not pretend to. Nothing
else stops: the screens, the alarm system and the protections work as
they always do. Recompile in Logic Studio and install the project again.
