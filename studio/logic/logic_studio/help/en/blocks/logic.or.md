### Truth table

| In1 | In2 | Out |
|---|---|---|
| 0 | 0 | 0 |
| 1 | 0 | **1** |
| 0 | 1 | **1** |
| 1 | 1 | **1** |

An unconnected input counts as FALSE. A **stubbed** input (see [Input stub](help:concept_stubs)) is left out and the gate computes its result from the rest. The family as a whole: [Logic gates](help:concept_gates).

### 1. Common alarm

The sounder must go off when **any** protection trips: `Overload` OR
`Earth fault` -> `M.ALARM_ZBIORCZY` -> siren. With more sources:
[OR-3](help:block:logic.or3), [OR-4](help:block:logic.or4) or a cascade.

### 2. Control from two places

Corridor lighting switches on from the button at the entrance **or** the
panel: `DI button 1` OR `panel bit M.SWIATLO` -> the S input of an
[SR](help:block:memory.sr) latch.

### 3. A stop condition

The pump must stop on `STOP from panel` OR `Dry run` OR `Overheating`.
The OR result goes to the R input of the latch holding the pump running -
see [Typical control circuits](help:guide_typical_circuits).
