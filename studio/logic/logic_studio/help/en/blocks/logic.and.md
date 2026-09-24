### Truth table

| In1 | In2 | Out |
|---|---|---|
| 0 | 0 | 0 |
| 1 | 0 | 0 |
| 0 | 1 | 0 |
| 1 | 1 | **1** |

An unconnected input counts as FALSE. A **stubbed** input (see [Input stub](help:concept_stubs)) is left out and the gate computes its result from the rest. The family as a whole: [Logic gates](help:concept_gates).

### 1. Permission to switch on - every condition at once

A pump contactor may only close when **supply is present** and **there is
no fault** and **the main breaker is closed**. Each condition is one gate
input; for three take [AND-3](help:block:logic.and3). Feed the result to
a "Bit output (internal)" block writing an OUT bit, e.g. `M.PUMP_ZEZW`,
and name that bit as the apparatus's **Permission** in Studio's apparatus
register - the controller refuses a CLOSE while the bit is FALSE, with a
reason naming the bit.

### 2. Confirmation from two sources

"Gate closed" is true only when **both** limit switches (left and right
leaf) say so: `DI limit L` AND `DI limit R` -> "CLOSED" lamp.

### 3. Sequential arming

START works only after ARM was pressed: `ARM` AND `START` -> a pulse into
[TP](help:block:timer.tp) or the S input of an [SR](help:block:memory.sr)
latch. Protects against a start by one accidental press.
