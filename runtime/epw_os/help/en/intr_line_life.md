# Line Life and Silence Detection

Not a self-test — the program never actively probes a sensor, since
many don't support that. This is a passive observation, kept for every
supervision line automatically, with no configuration needed:

- how many violations it's registered since it was added
- when it was last violated
- total time spent in the violated state
- when it registered its very first violation

It reuses the same record-keeping shape the program already uses for
device switching counts, saved the same durable way, rather than
building a second, parallel mechanism just for this.

**Maximum time without violation** (Engineer level, per line,
Configure Lines) — optional, 0 = off. If a line goes this long without
registering even one violation, it's marked **Suspect**: probably a
dead detector or a cut cable that happens to be sitting in its secure
position. This is a **warning, not an alarm** — shown on the Intrusion
Alarm page and written to the audit log, but it never raises an alarm
or affects arming. A perfectly quiet, working sensor and a dead one
look identical from the outside; this only flags the *possibility*
after an unusually long silence, for a person to go check.
