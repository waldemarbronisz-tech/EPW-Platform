# Power Supervision

A single, page-level check (not per-zone, not per-line) that mains
power and a backup battery are actually healthy — **Power
Supervision...** on the Configuration page (Engineer level).

Configure up to two, fully independent and optional inputs:
- a **mains presence** Digital Input, and which of its two states means
  "mains OK"
- a **battery status** Digital Input, and which of its two states means
  "battery OK"

Leaving either blank means that one simply isn't supervised — no error,
nothing shown, exactly as if this feature didn't exist. Configure only
the one you have, or neither.

A failed mains or battery reading raises a **technical alarm** — a
separate category from the intrusion (break-in) alarm, since a power
issue isn't a break-in. It is written to the audit log and published as
tags (see [Signals for Logic](help://intr_tags)) — `Security.System.
TechnicalAlarm`, and the per-input `Security.Power.MainsOk`/
`BatteryOk` — so a logic program can react to it (e.g. drive an
indicator or a notification). No page in this program currently
displays it on screen by itself; today, seeing it means checking the
Audit Log, watching the tag itself (e.g. from Trends or the REST API),
or reacting to it from logic.

**A mains failure never blocks arming or disarming** — the two are
completely independent. A zone arms and disarms exactly as it always
did regardless of the current power state.
