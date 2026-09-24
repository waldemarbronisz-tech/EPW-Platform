# Latches and edge detection

Gates compute the state "now". When the logic must **remember** (the
drive runs after the button is released, an alarm persists until
cleared) or react to the **moment** of a change rather than to a state
(one press = one count), the stateful blocks on this page are needed.

## SR and RS latches

| | S and R together | When to choose |
|---|---|---|
| [SR](help:block:memory.sr) | **S1** (Set) wins | alarm memory: clearing does nothing while the cause persists |
| [RS](help:block:memory.rs) | **R1** (Reset) wins | drives: STOP/fault/interlock always wins over START |

Both remember Q between scans; when the logic starts Q = FALSE. Setting
and clearing may come from different sources (a physical button, an IN
bit from the panel or from a synoptic push button, another piece of
logic) - gather them with an [OR](help:block:logic.or) before the input.

Safety rule: if any of the R sources is STOP, a safety switch or an
interlock, use **RS**. The set-dominant SR is right where **not losing**
an event matters more (alarm memory).

## Edge detection

| Block | A one-scan pulse when... |
|---|---|
| [R_TRIG](help:block:edge.rtrig) | the input changed 0->1 |
| [F_TRIG](help:block:edge.ftrig) | the input changed 1->0 |
| [CHANGE](help:block:edge.change) | the input changed either way |

The output lasts **exactly one scan**. For the eye (a lamp) and for slow
consumers that is too short - stretch it with a [TOF](help:block:timer.tof)
or [TP](help:block:timer.tp). For counters and latches one scan is enough.

In the first scan after the logic starts the "previous state" is FALSE:
an input that is TRUE right away gives one R_TRIG/CHANGE pulse. If that
is unwanted (counting, say), block it during start-up with a condition
from a [TON](help:block:timer.ton).

## Three classic connections

1. **Toggle by a button**: `Button` -> R_TRIG -> CU of a
   [CTUD](help:block:counter.ctud); state = CV odd. Or simpler: a synoptic
   push button in "toggle" mode writes the IN bit itself.
2. **The "cycle finished" event**: F_TRIG(`Cycle running`) -> S of the
   next sequence step's latch.
3. **A latched alarm**: `Cause` -> S1 of an SR, `Clear` -> R, Q -> lamp.
   Clearing works only once the cause is gone.

Details and more examples: [Typical control
circuits](help:guide_typical_circuits).
