### How it works

- LD = TRUE loads CV with PV (the pin, or the "Preset" property) and wins
  over CD.
- Every **rising edge** of CD decrements CV by 1.
- Q = TRUE when CV <= 0. The counter keeps counting below zero.

Full description: [Counters CTU, CTD, CTUD](help:concept_counters).

### 1. Cycles left until replacement

Load 500 (LD when a new part is fitted), subtract one per cycle; Q ->
"replace the part". CV shows how many are left.

### 2. Counting portions down

Load the number of portions to dispense, every dispenser pulse subtracts
one; at zero close the valve.
