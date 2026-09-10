# Supervised Lines

Each line is one supervised input, assigned to a zone. The table shows
Id/Name/Zone/Type; the **Configure...** button opens the full setup:

- **Input Mode** — Contact (a digital DI input) or Parametrized (an
  analog AI input with an end-of-line resistor).
- **Resistor Type** — **EOL** (single) or **2EOL** (double) —
  parametrized mode only. 2EOL additionally distinguishes Short and
  Tamper; EOL only Violated/Secure/Open Fault.
- **Value Windows** — Min/Max ranges (engineering units) for each
  recognized line state.
- **Confirmation Time (sensitivity)** — how long a violation must
  persist before it counts (filters brief glitches).
- **Violation Count (multiplicity)** — how many violations within the
  time window are required to trip (set to 2 for "double-knock").
- **Lockout After Alarm Count** — auto-locks the line after a run of
  alarms in one arm cycle.
- **Alarm Hold Time** — how many seconds until the alarm auto-clears
  (0 = holds until disarm).
- **Silence Time Before Suspect** — no violation for this long marks
  the line suspect (a warning, not an alarm).

Line types: **Instant** (alarms only while the zone is armed),
**Delayed** (starts the entry countdown), **24-Hour** (always alarms,
regardless of arming), **Supervisory** (never alarms, only signals).
