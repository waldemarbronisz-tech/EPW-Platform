### Truth table

| In1 | In2 | Out |
|---|---|---|
| 0 | 0 | **1** |
| 1 | 0 | 0 |
| 0 | 1 | 0 |
| 1 | 1 | **1** |

XNOR is [XOR](help:block:logic.xor) with its output negated: TRUE when the
inputs are **equal**. An unconnected input counts as FALSE. A **stubbed** input (see [Input stub](help:concept_stubs)) is left out and the gate computes its result from the rest. The family as a whole: [Logic gates](help:concept_gates).

### 1. Command agrees with feedback

`Command CLOSE` XNOR `Feedback CLOSED` -> TRUE when the apparatus is in
the state it should be. Through a [TOF](help:block:timer.tof) or
[TON](help:block:timer.ton) allow the switching time before FALSE reports
"the apparatus did not execute the command".

### 2. Two drives kept in step

Two gates must always be in the same position: `Gate 1 open` XNOR
`Gate 2 open` = FALSE -> mismatch -> stop both.
