# EPW Studio

EPW Studio is a single engineering application for designing EPW
platform installations: synoptic diagram, control logic, point registry,
apparatus, intrusion alarm, protection settings and the controller
connection — all in one window, one project tree.

**Screens (Synoptic Editor) and Logic (Logic Studio) are departments of
Studio**, not separate programs — launching each one standalone is no
longer how this is used.

## If this is your first time here

Read [How a project is built, step by step](help://workflow). That is
the whole road: from an empty file to a controller running your project
— twelve steps, each linking to the department where you do it.

Then: [The Studio window](help://window) — the tree, the toolbars, how
unsaved edits are marked, F1.

## What a project is

One `projekt.epw` file = one controller. It holds **everything** that
controller needs to know: the device composition, cards, points,
apparatus, screens, the compiled logic, the intrusion alarm, protection
settings, MQTT. The controller needs nothing else — see [Saving,
revisions and settings](help://save_versioning).

What a project never holds: passwords, keypad codes and tokens. Those
are secrets of one controller, not of the installation — they live in
its own local files and never travel to Studio, into git or over the
network.

## Object and devices

The left column starts with the DEVICE LIST: an object (a house, a
plant) and its controllers, each its own `projekt.epw` in its own
folder, tied together by an `obiekt.epwsite` file. Clicking a controller
switches the whole tree below to its project. Details: [An object of
several controllers](help://site).

A plain single `projekt.epw` still works as before — as a
one-controller object.

## Where to look next

- **The project** — every branch of the tree, field by field.
- **Intrusion alarm**, **Protection**, **Integration** — modules that
  appear in the tree only when they are in the [device
  composition](help://devices).
- **The controller** — sending the project, live settings, tests,
  counters.
- **Working with a project** — checking, saving, versioning, glossary.
