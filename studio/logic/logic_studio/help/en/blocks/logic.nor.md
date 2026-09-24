### Truth table

| In1 | In2 | Out |
|---|---|---|
| 0 | 0 | **1** |
| 1 | 0 | 0 |
| 0 | 1 | 0 |
| 1 | 1 | 0 |

NOR is [OR](help:block:logic.or) with its output negated - TRUE only when
**no** input is active. An unconnected input counts as FALSE. A **stubbed** input (see [Input stub](help:concept_stubs)) is left out and the gate computes its result from the rest. The family as a whole: [Logic gates](help:concept_gates).

### 1. "All well" lamp

`Alarm 1` NOR `Alarm 2` -> green lamp: lit as long as there is no alarm,
out at the first one.

### 2. Permission with no interlock active

`Service interlock` NOR `Protection interlock` -> `M.ZEZW`: permission
exists when no interlock is active. Clearer than NOT + NOT + AND.
