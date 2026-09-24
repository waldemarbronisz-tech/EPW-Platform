### Truth table

| In1 | Out |
|---|---|
| 0 | **1** |
| 1 | 0 |

An unconnected input counts as FALSE. A **stubbed** input (see [Input stub](help:concept_stubs)) is left out and the gate computes its result from the rest. The family as a whole: [Logic gates](help:concept_gates).

### 1. A normally-closed contact (NC)

STOP buttons and safety switches are usually **normally closed**: at
rest they give TRUE on the input, pressed they give FALSE. For the logic
to count "pressed", negate the input: `DI STOP (NC)` -> NOT ->
`M.STOP_WCISNIETY`. A broken wire also reads "pressed" - that is
deliberate (fail-safe).

### 2. Negating a condition for a permission

Permission exists when there is **no** alarm: `Alarm` -> NOT -> an input
of the permission [AND](help:block:logic.and). With several negated
conditions consider [NOR](help:block:logic.nor) instead of several NOTs.

### 3. An inverse lamp

The "STOP" lamp is lit when the drive is **not** running: `Drive running`
-> NOT -> `DO STOP lamp`.
