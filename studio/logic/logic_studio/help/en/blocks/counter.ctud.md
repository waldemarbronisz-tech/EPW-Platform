### How it works

- CU increments and CD decrements CV (each on its own rising edge; both
  in one scan cancel out).
- R clears (highest priority), LD loads PV (before CU/CD).
- QU = TRUE when CV >= PV; QD = TRUE when CV <= 0.

Full description: [Counters CTU, CTD, CTUD](help:concept_counters).

### 1. People / vehicles in a zone

Entry -> CU, exit -> CD, PV = capacity; QU -> "car park full", QD -> "car
park empty". R from the panel for a manual correction.

### 2. Batches in a buffer tank

A filled batch -> CU, a drawn batch -> CD; QU blocks the next fill, QD
blocks drawing.
