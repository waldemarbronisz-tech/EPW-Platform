# Counters CTU, CTD, CTUD

A counter counts **rising edges** on its counting input - a held signal
counts once. CV is shown on the canvas in simulation ("CV=..."), and Q
says whether the preset has been reached.

| Block | Counts | Load/clear | Q |
|---|---|---|---|
| [CTU](help:block:counter.ctu) | up (CU) | R clears (wins) | CV >= PV |
| [CTD](help:block:counter.ctd) | down (CD) | LD loads PV (wins) | CV <= 0 |
| [CTUD](help:block:counter.ctud) | up (CU) and down (CD) | R clears > LD loads > CU/CD | QU: CV >= PV, QD: CV <= 0 |

PV comes from the PV pin, or from the "Preset" property when the pin is
not connected. The counter keeps counting past PV (CTU) and below zero
(CTD) - Q simply stays TRUE.

## Worth knowing

- **An edge, not a state.** A CTU with CU fed by a signal lasting many
  scans counts it once. When counting a compound event, an
  [R_TRIG](help:block:edge.rtrig) before CU documents the intent on the
  diagram, though technically it is not required.
- **CV does not survive a restart.** After a controller restart and after
  stopping the simulation the counter starts from zero (CTU) or from PV
  after LD. A lasting count needs a write to a retentive register (MWR.)
  or the panel's switching counters (Point register -> counters).
- **Two edges in one scan** (CTUD, CU and CD together) cancel out.
- **Q as a condition**: a counter's Q is usually a long-lasting signal
  (it persists while CV >= PV). If you need a "reached" pulse, pass Q
  through an [R_TRIG](help:block:edge.rtrig).

## Typical uses

- operations until service (CTU, cleared from the panel),
- a limit of start attempts (CTU + automatic-mode lock-out),
- cycles left (CTD, LD when a part is replaced),
- an in/out balance - people, vehicles, portions (CTUD, QU "full", QD
  "empty").

Circuits drawn out: [Typical control circuits](help:guide_typical_circuits).
