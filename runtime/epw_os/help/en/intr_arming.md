# Arming, Disarming, and Entry/Exit Delays

Arming and disarming a zone requires **Operator level or higher**, from
the Overview page (or from logic — see
[Signals for Logic](help://intr_tags)).

A zone's states:

- **DISARMED** — not watching (except any 24-Hour line, which always
  watches).
- **EXIT DELAY** — arming was just requested and the zone has an exit
  delay configured; counts down, then becomes ARMED. Gives time to
  leave without tripping anything.
- **ARMED** — actively watching every line in the zone.
- **ENTRY DELAY** — a Delayed-type line was violated while ARMED;
  counts down, giving time to disarm before it becomes an ALARM.
- **ALARM** — a violation the zone's current state didn't excuse.
  Disarming the zone (Operator+) always clears it, from any state.

**If a line is already violated at the moment you try to arm**, the
program tells you which one(s) and refuses to arm silently — you must
explicitly confirm arming anyway. This can't happen by accident.

**The same applies to a line in fault** (tamper, short circuit, open
circuit, or undetermined — see
[Input Modes](help://intr_input_modes)): arming requires the same
explicit confirmation, naming which line and that it's a fault rather
than a plain violation. Arming is still possible — the confirmation
just makes sure it isn't done unknowingly — and doing so is written to
the audit log distinctly, as arming *despite* a fault.

The countdown seconds remaining show on the Overview page for
any zone currently in EXIT DELAY or ENTRY DELAY, and the aggregate
system state always shows in the status bar.
