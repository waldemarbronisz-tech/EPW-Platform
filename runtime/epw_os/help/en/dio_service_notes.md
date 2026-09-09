# Service history (notes)

Complements the [switching counter](help://dio_switching_counters): the
counter says HOW MANY times a device operated; a note says WHAT
HAPPENED to it. Together they give the device's full history, not just
its current state.

## What this is not

A service note is **not the same** as the [audit log](help://ea_audit_log).
The audit log writes itself automatically for certain system actions
(logging in, changing a setting). A note is always written by a
person, by hand, when they decide something is worth recording - the
program never adds one on its own.

## What an entry contains

- Text - whatever the operator types,
- the date and time it was written,
- the access level it was written at (Operator or Engineer - User
  cannot add an entry).

## Where to find it

- **Digital Inputs** and **Control Outputs** - a **Notes...** button in
  its own column, on every row.
- **Main View** - the device window (click a breaker/contactor) →
  **Properties** button → **Notes** tab.

Viewing entries is available at every access level, with no
restriction at all - including User.

## Adding an entry

Requires **Operator** level or above. The text box and Add button are
disabled below that level.

## Entries can't be corrected or deleted

This is deliberate - service history is a logbook, not a notepad. No
access level, including Engineer, can edit or delete an existing
entry. A mistake is corrected by adding ANOTHER entry with the
correction - the same way a paper logbook works: you never erase a
mistake, you write a correction underneath it.

## Exporting to CSV

The **Export to CSV...** button (in the device's Properties window on
Main View, and in the notes window opened from the DI/DO tables) saves
one CSV file containing both the device's current data (description,
switching counters where available) and its full note history, oldest
first. Note text in the export is exactly what was typed - never
translated or altered in any way.
