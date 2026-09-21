# Zones

A zone is a part of the site armed and disarmed as one: the ground
floor, the hall, the garage. Every [supervised line](help://lines)
belongs to exactly one zone.

| Column | Meaning |
|---|---|
| **Id** | unique, e.g. `Z1` — the zone appears under this id in tags and in logic |
| **Name** | readable; this is what the panel shows |
| **Exit delay (s)** | how long you have to leave after arming |
| **Entry delay (s)** | how long you have to disarm after a delayed line is violated |

A zone that still has lines assigned **cannot be removed** — reassign or
remove its lines first.

## Power supervision

Two independent, optional checks: **Mains (230 V)** and **Battery**,
each naming a point and whether the "OK" state is high.

The platform's convention: **a healthy signal reads high**, so a severed
cable or a dead module fails low and looks like a fault rather than like
a normal state. An unconfigured check always reads healthy — "no
configuration means no supervision", with no errors.

## Sounder

These are **settings**, not an output. The controller drives no siren —
it publishes state (`SEC.SYSTEM.SIREN_ACTIVE`, `SIREN_TIME_LEFT`,
`STROBE_ACTIVE`, `PANIC`), and you wire the output in
[Logic](help://logic), through whatever interlocks the installation
needs.

| Setting | Meaning |
|---|---|
| **Sound for at most** | after this, `SIREN_ACTIVE` goes false on its own although the alarm carries on; `0` = no limit |
| **A panic line does not sound the siren** | ticked by default — see the [Panic](help://lines) line type |

The light (`STROBE_ACTIVE`) outlives the noise: on from the alarm until
somebody clears the alarm memory, so a person coming back to the site
sees that something happened.
