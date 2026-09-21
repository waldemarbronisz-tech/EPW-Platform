# Night Arming (Partial Arming)

Arming a zone **fully** watches every line in it. Arming it **at night**
watches only the lines flagged to watch at night — so people can move
about inside a building whose perimeter is still guarded.

## Where the two buttons are

On the Overview page, a zone offers **Arm** and, next to it, **Arm
(night)** — but only when night arming would actually protect something
different. A zone whose every line watches at night is protected
identically either way, so there is nothing to choose between and only
one button appears.

## Which lines keep watching

Each supervised line carries a **Watches at night** flag, set in Studio.
Unticked is the usual choice for motion detectors inside.

Two line types ignore the flag entirely and alarm in any case:

- **24-Hour** — a tamper switch does not care how the zone is armed, or
  whether it is;
- **Panic (hold-up)** — a hold-up button that only worked while the
  building was armed would be worse than none.

A **line fault** (tamper, short, cut cable) also alarms regardless, on
every line type.

## A line excluded at night does not block arming

Refusing a night arm because the hall motion detector can see the person
doing the arming would make the whole mode useless. Only lines that
actually watch at night are checked for readiness.

## What the zone shows afterwards

The zone's row says which mode it is armed in, so "armed" never hides
the difference between the whole building and its perimeter.

Disarming always returns the zone to full arming for next time: a zone
armed at night must not quietly arm at night again when somebody presses
plain **Arm**.

## In logic

`SEC.SYSTEM.ARMED` requires every zone armed **fully**. `SEC.SYSTEM.ARMED_PARTIAL`
covers both "some zones armed" and "armed, but only at night".
`REQ.SEC.ARM_ALL_PARTIAL` arms every zone at night. See [What the Logic
Program Can See](help://logic_signals).
