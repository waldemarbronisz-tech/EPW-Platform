### How it works

Out is TRUE for **one scan** - the one in which In changed from TRUE to
FALSE. Full description: [Latches and edge
detection](help:concept_memory_edges).

### 1. A "finished" event

The end of a pump run (the moment it stops) must start the filter flush:
F_TRIG(`Pump running`) -> S of the flush sequence latch.

### 2. Counting cycles once complete

A cycle counts as done only after it ends: F_TRIG(`Cycle running`) -> CU
of a [CTU](help:block:counter.ctu).

### 3. Detecting a button release

The action follows the release of the button ("release to execute"):
F_TRIG(`DI button`) -> [TP](help:block:timer.tp).
