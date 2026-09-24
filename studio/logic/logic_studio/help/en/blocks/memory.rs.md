### How it works

| R1 | S | Q |
|---|---|---|
| 0 | 0 | unchanged (remembers) |
| 0 | 1 | **1** |
| 1 | 0 | 0 |
| 1 | 1 | 0 - Reset dominates |

Like [SR](help:block:memory.sr), but when both inputs are active, **R1**
wins. This is the safer choice wherever R is STOP, a fault or an
interlock: even a held START button cannot keep the drive running while
STOP persists. Full description: [Latches and edge
detection](help:concept_memory_edges).

### 1. Drive start/stop with stop priority

`START` -> S, `STOP` OR `Fault` OR `Interlock` ([OR-3](help:block:logic.or3))
-> R1, Q -> `DO contactor`. Drawn step by step in [Typical control
circuits](help:guide_typical_circuits).

### 2. Arming with automatic disarm

`Arm` -> S, `Tamper` OR `Disarm` -> R1. A tamper always disarms, whatever
the held arm button says.
