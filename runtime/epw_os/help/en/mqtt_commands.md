# Control from Home Assistant

The MQTT link is not a one-way view any more. Home Assistant can **arm**
the alarm system (fully or at night), **disarm** it, **clear** an alarm,
**silence** the sounder, change protection **settings** and **command**
apparatus.

[Forces](help://dio_force) are deliberately not on that list — a force
is a tool for somebody standing at the cabinet, kept alive by their
presence.

## Who is allowed

**Home Assistant has one MQTT account.** Everybody clicks in HA, but the
broker always sees the same client and cannot tell two people apart. So
identity travels **inside the message**: each person's own **remote
token**, issued on this panel and shown once — see [Alarm System
Users](help://intr_users).

Permissions are then exactly the panel's own: the person's level and the
zones they may operate, checked by the same managers, not a second set
of rules that could drift.

## What is refused, and why

| Refused | Why |
|---|---|
| a **retained** message | the broker replays it to everyone who connects, including this controller after a power cut — "disarm" sent once would then disarm the site on every restart |
| not JSON, or no command id | there is nothing to identify or answer |
| a timestamp older than 120 s | an intercepted message is useless a minute later |
| an unknown token, a disabled person, or a token belonging to somebody other than the message claims | impersonation |
| too low a level, or not their zone | the same rule as at the keypad |

A **duplicate command id** is not refused — MQTT's "at least once" makes
duplicates ordinary — it is simply **not executed twice**, and the
previous answer is published again.

## Every refusal is a silent alarm

A refused command looks like somebody trying the door. It raises an EPW
alarm, `REMOTE_COMMAND_REFUSED` — silent in the literal sense: it does
not touch the sounder, which follows line violations, not rejected
messages. The alarm travels over MQTT like every other, so Home
Assistant is what turns it into a notification on a phone.

Accepted or refused, every command is written to the audit log **with
the person's name**.

## Where the real boundary is

If Home Assistant commands this controller, then **Home Assistant's own
security is the boundary**. Whoever takes it over sends commands with
the token stored there. This channel gives you attribution in the log,
per-person scope, and immunity to replays and duplicates. It does not
protect you from a compromised Home Assistant.

In practice: reach HA from outside (VPN or its own remote service), not
the broker; keep the broker in the local network, with TLS and its own
account; one token per person, never one shared token — otherwise the
log stops being able to say who did what.
