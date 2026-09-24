### How it works

Out is TRUE for **one scan** - the one in which In changed from FALSE to
TRUE. In the next scan Out is FALSE again, although In persists.

Mind the start: in the first scan after the logic starts the previous
state is FALSE, so an input that is TRUE right away gives one pulse.
Full description: [Latches and edge detection](help:concept_memory_edges).

### 1. A "change" button instead of a "hold" button

The operator presses once - the state must toggle: `DI button` -> R_TRIG
-> the CU input of a [CTUD](help:block:counter.ctud) or alternating S/R
of a latch. Without edge detection a held button would toggle the state
every scan.

### 2. Counting events

A [CTU](help:block:counter.ctu) reacts to the CU edge itself, but when
you count a compound event (an AND of several conditions), an R_TRIG in
front of CU says plainly on the diagram that the **moment** the condition
is met is what counts.

### 3. Capturing a value once

At the moment the pump starts, remember the tank level:
R_TRIG(`Pump running`) as the "store now" signal.
