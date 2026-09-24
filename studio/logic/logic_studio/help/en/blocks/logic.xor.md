### Truth table

| In1 | In2 | Out |
|---|---|---|
| 0 | 0 | 0 |
| 1 | 0 | **1** |
| 0 | 1 | **1** |
| 1 | 1 | 0 |

XOR is TRUE when the inputs **differ** (formally: when an odd number of
inputs is active). An unconnected input counts as FALSE. A **stubbed** input (see [Input stub](help:concept_stubs)) is left out and the gate computes its result from the rest. The family as a whole: [Logic gates](help:concept_gates).

### 1. Detecting inconsistent feedback

An apparatus has two auxiliary contacts, "closed" and "open". Correctly,
exactly one is active. `Contact CLOSED` XOR `Contact OPEN` = FALSE means a
discrepancy (both or neither) -> "position mismatch" alarm. Add a
[TON](help:block:timer.ton) so the travel time of the contacts does not
alarm.

### 2. Two-way switching

Lighting from two places without a latch: each switch changes the state -
`Switch A` XOR `Switch B` -> light.

### 3. Comparing two bits

Two independent paths computing the same thing (redundancy): XOR of
their results = TRUE -> they differ -> a signal to check.
