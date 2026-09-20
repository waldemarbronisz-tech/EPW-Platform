# Device Wizard

**File → Device Wizard.** It walks you through steps 1–4 of the
[project road](help://workflow), in the order the project needs them.
Nothing is written until you press **Finish**.

## 1. Project information

Name (required — the wizard will not continue without it), author,
description.

## 2. Device composition

Tick the modules this controller has. Modules already in the project
stay ticked; **removing a module is done in the [Device
Composition](help://devices) branch**, not here.

## 3. Locations

A code (letters A–Z and digits only, e.g. `KOT` for the boiler room)
plus a description. The wizard tells you straight away if a code has an
illegal character or repeats.

## 4. I/O cards

One row per physical module: id, model, the channel kinds ticked with
their counts, the Modbus address, the location. A card with both DI
**and** AI is one row with two ticks, not two rows.

Checked immediately: an empty id, a dot or a space in an id, a repeated
id, a card with no channel kind ticked, a repeated Modbus address.

## 5. Summary and next steps

A tally: how many modules, locations, cards and how many **points** will
be created. Below it the list of next steps in the tree — point
registry, apparatus, alarm/protection, screens, logic — and a reminder
that the wizard **does not save the file**: saving is yours, from the
top toolbar.
