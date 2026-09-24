### How it works

- Every **rising edge** of CU increments CV by 1 (a held CU does not keep
  counting).
- R = TRUE clears CV and wins over CU.
- Q = TRUE when CV >= PV (the PV pin, or the "Preset" property when it is
  not connected). The counter keeps counting past PV.
- CV is shown on the canvas in simulation ("CV=...").

Full description: [Counters CTU, CTD, CTUD](help:concept_counters).

### 1. Operations until service

Count the contactor's closings; at 10,000 request a service: CU <-
[R_TRIG](help:block:edge.rtrig)(`Feedback`), PV = 10000, Q -> `M.PRZEGLAD`,
R <- the IN bit `M.KASUJ_LICZNIK` from the panel (after the service).
Note: CV is not kept across a controller restart - for a lasting count
write CV to a retentive register (MWR.) or use the panel's switching
counters.

### 2. A limit of attempts

After three failed start attempts lock the automatic mode: CU <-
F_TRIG(`Start attempt`), PV = 3, Q -> `M.BLOKADA_AUTOMATU`, R <- a
successful start OR a clear.

### 3. Batch dosing

Every sensor pulse is one portion; after PV portions close the valve and
clear: Q -> valve close and (through a [TP](help:block:timer.tp)) -> R.
