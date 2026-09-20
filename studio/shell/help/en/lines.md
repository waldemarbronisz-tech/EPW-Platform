# Supervised Lines

One line = one detector (or loop of detectors) on one input point. The
table shows the id, name, zone, type and a summary of the configuration;
the rest is in the **Configure…** dialog — fourteen fields is not a
table row.

Without a [zone](help://zones) a line cannot be added.

## Line types

| Type | When it alarms |
|---|---|
| **Instant** | the moment it is violated, but only while the zone is ARMED |
| **Delayed** | a violation while armed starts the entry countdown; it alarms only if nobody disarms |
| **24-Hour** | immediately, **regardless of the zone's state** — tamper, a protected panel |
| **Supervisory** | **never** alarms on a violation; it signals it to the logic (lighting control, say). A *fault* on it alarms like on any other type |
| **Panic (hold-up)** | like 24-hour — any zone state, night arming included — but **silent by default**: the point is that the person standing over you does not learn you pressed it |

## The input

**Contact mode** — an ordinary contact: a point plus a normal state,
**NC** (normally closed) or **NO** (normally open). The line reads only
as secure or violated.

**Parametrized mode (EOL/2EOL)** — an end-of-line resistor, single (EOL)
or double (2EOL). One analog value then yields five states instead of
two: **Secure**, **Violated**, **Open fault**, **Short**, **Tamper**.
The value windows (min/max in engineering units) are set in the table
below — one row per state.

This is exactly why 2EOL detects a cut or a bridged cable, which a plain
contact cannot.

## False-alarm filtering

| Setting | What for |
|---|---|
| **Confirmation time (sensitivity)** | a violation shorter than this is ignored |
| **Violation count (multiplicity)** | it alarms only after N violations |
| **Multiplicity window** | the time they must fall within |
| **Lockout after alarm count** | a "chattering" line stops alarming until disarm |
| **Alarm hold time** | how long the zone stays in ALARM after the cause ends |

## Line supervision

**Silence time before suspect** — if the line has reported no violation
for this long, it is marked "suspect". This is a **warning, not an
alarm**: a detector that never sees anything may be a dead detector.

## Night arming

**Watches at night** — unticked means this line stops supervising while
its zone is armed in night mode. The usual choice for motion detectors
inside: people move about the house while the perimeter still watches.
24-hour and panic lines alarm regardless.
