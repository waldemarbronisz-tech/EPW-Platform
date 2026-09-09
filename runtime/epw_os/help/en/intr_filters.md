# False-Alarm Filtering

Each supervision line can be given up to four extra parameters (Engineer
level, in the same Configure Lines dialog as its type and normal state)
that make a plain sensor behave more like an expensive one with
built-in filtering. Every one of them defaults to **off** — a line added
before this existed, or one where you never touch these fields, behaves
exactly as if none of it existed.

**Minimum violation time** — the input must stay tripped longer than
this before it counts as a violation at all. Filters a brief glitch or
contact bounce: a trip shorter than the threshold never reaches the
`Security.Line.<id>.Violated` tag, never alarms, and never counts
toward anything below. 0 = off.

**Violations needed / within** — how many separate violations, within
a time window, are required before the line actually alarms. A single
violation below the threshold does nothing; reaching the count within
the window alarms immediately, and the count then starts over. If no
further violation arrives before the window runs out, the count resets
to 0 on its own — a lone violation, long ago, is never added to a new
one much later. 1 violation needed = off (every violation alarms on its
own, as usual).

**Auto-lock after** — after this many alarms from the *same line* within
one arm cycle, the line automatically locks: it stops alarming
entirely, silently, until the zone is disarmed. Protects against one
line stuck flapping and re-alarming over and over. A locked line shows
"(auto-locked)" next to its state on the Overview page, and the
lock itself is written to the audit log. Disarming the zone always
clears every line's lock (and its alarm count) for that zone, so the
next arm cycle starts with a clean slate. 0 = off.

**Alarm hold time** — once a line raises an ALARM, this is the minimum
time that state is held. Once it has elapsed, if the line is no longer
violated, the zone returns to ARMED automatically — no need to manually
disarm and re-arm for something that already cleared on its own. If the
line is *still* violated when the hold time elapses, the zone stays in
ALARM (checked again the moment the line actually clears). 0 = off — the
zone stays in ALARM until someone disarms it, same as every line that
doesn't set this.

None of this changes what a line's type does, how arming works, or
what the module does with a violation once it decides to alarm — see
[Line Types](help://intr_line_types) and
[Arming, Disarming, and Delays](help://intr_arming). The module still
never drives an output itself either way — see
[Signals for Logic](help://intr_tags) for the two new tags
(`MultiplicityCounting`, `Locked`) these filters publish.
