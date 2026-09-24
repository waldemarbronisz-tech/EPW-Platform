### How it works

Out is TRUE for **one scan** on every change of In - 0->1 and 1->0
alike. It is [R_TRIG](help:block:edge.rtrig) OR
[F_TRIG](help:block:edge.ftrig) in one block. Full description: [Latches
and edge detection](help:concept_memory_edges).

### 1. Recording every change of position

Every change of an apparatus's state must increment its switching
counter: CHANGE(`Feedback CLOSED`) -> CU of a [CTU](help:block:counter.ctu).

### 2. Triggering a message

Show a message on the panel on every mode change: CHANGE(`M.AUTO`) -> a
system message block.

### 3. Chatter detection

Too many changes in a short time mean a chattering contact: CHANGE ->
[CTU](help:block:counter.ctu) cleared every 10 s by a [TON](help:block:timer.ton);
the counter's Q at PV = 5 -> "check the contact".
