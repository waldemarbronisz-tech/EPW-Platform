### Truth table

| In1 | In2 | Out |
|---|---|---|
| 0 | 0 | **1** |
| 1 | 0 | **1** |
| 0 | 1 | **1** |
| 1 | 1 | 0 |

NAND is [AND](help:block:logic.and) with its output negated. An unconnected input counts as FALSE. A **stubbed** input (see [Input stub](help:concept_stubs)) is left out and the gate computes its result from the rest. The family as a whole: [Logic gates](help:concept_gates).

### 1. "Not both at once" interlock

Two drives must not run together (a pump and a stirrer on one supply):
`Pump running` NAND `Stirrer running` -> permission to start the next
one. While at most one runs, NAND gives TRUE.

### 2. A NOT + AND in one block

Where you need "condition A and B -> **switch off**", NAND saves a block:
feed its result straight to an output that is active at rest (e.g.
`M.ZEZW_PODTRZYMANIE`).
