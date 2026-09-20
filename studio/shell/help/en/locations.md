# Locations

The places cards and points refer to: a cabinet, the boiler room, the
gate, the hall.

| Column | Rule |
|---|---|
| **Code** | short, **letters A–Z and digits only**, unique (e.g. `KOT`, `GATE1`) |
| **Description** | the full name a human reads |

## Inheritance

A card sits in one location. **Every point on it inherits that
location** until you give it one of its own in the [Point
Registry](help://points) — the registry then shows "(inherited: …)".

This is why moving a card to another cabinet is one edit, not
thirty-two.

## What this is really for

The information travels to the controller and lands on the tag. A
technician at the cabinet sees not only "ELA1.DI.7 — hall detector" but
also where that terminal physically is. Without it you are left with a
question nobody can answer two years later.

A point naming a location that is not on the list is reported by [Check
Project](help://validation).
