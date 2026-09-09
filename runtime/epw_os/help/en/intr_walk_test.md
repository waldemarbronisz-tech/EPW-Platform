# Walk-Test Mode

A way to walk through the premises and confirm every sensor actually
reacts, without setting off a real alarm while you do it.

**Starting it** — Engineer level, the **Walk-Test Mode** button on the
toolbar above the zone list. Pick a zone and, optionally, how long it
should run (defaults to 30 minutes) — it always ends on its own after
that, so it can never stay on by being forgotten. The remaining time is
shown live while it runs.

**While it's running**, on that zone:
- A line being violated is still recorded and shown on screen — the
  dialog lists every line in the zone with whether it has reacted yet
  and, if so, when.
- It **never raises an alarm and never changes the zone's state** — the
  whole point is to check sensors without the household waking up or a
  real dispatch being triggered.
- A line **fault** (sabotage, short, open circuit, undetermined) is a
  different matter entirely — those still alarm normally, exactly as
  they would with walk-test off. Walk-test only quiets a *violation*'s
  reaction, never a fault's — see
  [Input Modes: Contact vs. Parametrized](help://intr_input_modes) for
  what counts as a fault.

**Ending it** — the Stop button (by hand) or the configured duration
running out (on its own) both end it the same way: a summary of which
lines confirmed and which stayed silent for the whole test, so you know
immediately what still needs checking before you leave. Starting,
stopping, and an automatic end are all recorded to the audit log and to
the [alarm event history](help://intr_history).

Nothing about a zone's arming, its line types, or the false-alarm
filters on any line changes while walk-test runs — see
[Arming, Disarming, and Delays](help://intr_arming) and
[False-Alarm Filtering](help://intr_filters).
