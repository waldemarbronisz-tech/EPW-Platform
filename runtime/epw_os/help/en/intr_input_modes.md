# Input Modes: Contact vs. Parametrized (EOL/DEOL)

Every supervision line uses exactly one of two, mutually exclusive
input modes, chosen in Configure Lines (Engineer level):

**Contact (digital)** — the default, and what every line used before
this existed. Bound to a Digital Input and its normal (secure) state,
Normally Closed or Normally Open — see
[Zones and Supervision Lines](help://intr_zones_lines). Only two
states: **Secure** or **Violated**. A cut cable looks exactly like a
quiet sensor.

**Parametrized (analog)** — bound to an analog point instead, read
through one of two schemes:
- **EOL** (End-Of-Line resistor) — 3 states: Secure, Violated, Open
  circuit.
- **DEOL** (Dual End-Of-Line) — 5 states: Secure, Violated, Tamper,
  Short circuit, Open circuit.

Each state has its own configurable **value window** (low–high) the
reading must fall inside to count as that state — set from sensible
defaults, but always adjustable, since the actual resistor values
depend on the field wiring and are never hard-coded. A reading that
doesn't fall inside *any* configured window reads as **Undetermined** —
treated exactly like a fault (below), not silently ignored.

**Tamper, Short circuit, Open circuit, and Undetermined are all line
faults** — a fault alarms immediately, in every zone state, the same
way a 24-Hour line does, regardless of whether the zone is armed, **for
every line type without exception, Supervisory included**. A fault is a
different kind of event from a plain violation — a severed cable or a
removed tamper resistor is sabotage or a maintenance problem on any
line, not "motion in front of a sensor" — see
[Line Types](help://intr_line_types) for why Supervisory's own "never
alarms" rule is specifically about a violation, not a fault. See
[Signals for Logic](help://intr_tags) for the tags a fault publishes.

**The input picker only ever lists inputs of the right kind** — Contact
mode only offers Digital Inputs, Parametrized mode only offers analog
points; assigning the wrong kind isn't possible from this dialog.
Changing a line's mode clears whichever input was selected (a warning
says so first) — the old assignment doesn't silently carry over, since
it may no longer even make sense for the new mode.
