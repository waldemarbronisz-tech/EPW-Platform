# Bypassing a Line

A line can be temporarily excluded from arming/alarm checks — **Bypass**,
next to it on the Overview page (Engineer level). While
bypassed, the line's violated state always reads secure to the rest of
the system (arming and alarming both ignore it entirely), regardless of
what the underlying sensor is actually reporting.

Use this for a sensor you know is faulty or intentionally left open,
without having to remove and re-add its whole configuration.

Every bypass — turning it on or off — is written to the audit log with
who did it, when, and which line. A bypass does **not** survive a
restart: the program always comes back up with nothing bypassed, so a
sensor can never be silently forgotten as excluded across a restart.

Bypassing a line does not clear an alarm already raised because of it —
disarm the zone for that (see
[Arming, Disarming, and Delays](help://intr_arming)).
