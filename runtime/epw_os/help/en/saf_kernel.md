# System Health Monitoring (safety_kernel)

In line with the principle
["the screen informs, the hardware protects"](help://saf_principle),
the system health monitor (safety_kernel) is a **sensor, not a
protection system**. It checks the state every 1 second, on its own
thread, so it never slows down control.

## What It Detects

For each configured device, any one of the following three conditions
counts as "unhealthy":

- the device hasn't responded in 3 consecutive check cycles in a row
  (a single lost packet is not a fault — hence a threshold of three,
  not one);
- tags belonging to the device haven't refreshed within their
  configured timeout;
- the driver thread servicing the device has stopped running.

The result is published as two kinds of tags for each device (plus an
aggregate for the whole system): a current state (changes on its own,
in both directions) and a fault latch (set when detected, cleared ONLY
by manual acknowledgement — exactly as described in
[Acknowledging and What It's For](help://alm_ack)). A fault that clears
on its own stays visible until someone acknowledges it.

## What It Does

Detecting an unhealthy state:

- raises an alarm on the Alarms page (through the same alarm mechanism
  as a communication failure or EMERGENCY STOP);
- records an entry to the audit log;
- **blocks issuing NEW control commands** until the system returns to a
  healthy state — and records that fact too.

## What It Deliberately Does NOT Do

This module **never sends any command to any output** — it does not
open or close any device, and it does not react to a detected fault on
its own. Its only reaction is to block new commands and signal the
problem. Deciding what to actually do about a detected fault (e.g.
safely shutting down a given circuit) belongs to user logic configured
separately — in the current version of the program, no such logic is
loaded yet.
