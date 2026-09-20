# Backing Up This Controller

**Settings → Back up this controller...**, Engineer level, audited.

The project is safe: it lives in EPW Studio, usually in version control,
and can be sent here over the network. Everything else exists **only on
this controller's card**:

- the switching counters — how many times each apparatus has operated,
  and for how long, since the day it was installed;
- the arming state — which zones were armed, and in which mode;
- the alarm memory, the bypasses, the line supervision counters;
- the retentive logic bits (`MR.` / `MWR.`);
- the audit log — the record of who did what;
- the local settings: language, retentions, the bus.

Lose the card and none of that comes back. A backup is how it does.

## What a backup does not carry

**No secrets.** Not the access PINs, not an alarm user's keypad code,
not a remote token, not the REST API tokens, not the MQTT broker
password.

A backup is a file that leaves the site: onto a laptop, into an email,
onto a memory stick in a van. A PIN is four digits, and a hash of four
digits is a lookup table away from being the PIN itself. So they stay
here.

What the backup carries instead is an **inventory** — who had a code,
who had a token, whether the API tokens and the broker password were
set. A restore turns that into a checklist naming exactly what to set
by hand. Re-issuing five codes from a list takes ten minutes.
Recovering four years of switching counters is impossible.

**No trend history.** Recorded measurements, not configuration, and
potentially enormous. A controller that comes back without its trends
is working; one that comes back without its arming state is lying about
the building.

## When to take one

Before a project change, after commissioning, and on a schedule if the
installation matters. The same file is also taken from Studio
(Controller → Controller backup) and over REST
(`GET /api/v1/controller/backup`).
