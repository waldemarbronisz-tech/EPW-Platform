# The Studio window

## The left column

From the top: the **DEVICE LIST** (the object and its controllers — see
[Object](help://site)), and under it the **project tree** of the active
controller.

The tree has a fixed structure, regardless of what is filled in:

- **PROJECT** — Information, Device Composition
- **CONFIGURATION** — Locations, Cards, Point Registry, Apparatus
  Registry, Synoptic Diagram, Logic, MQTT, Object Links, Service Notes —
  in the order a project needs them: each branch after the ones it
  builds on
- **INTRUSION ALARM** — Zones, Supervised Lines, Users
- **PROTECTION** — Electrical, Process
- **CONTROLLER** — Connection, Protection Tests
- **Help**

Branches of modules outside the [device composition](help://devices) are
hidden.

## Where your unsaved edits are

A branch you edited is **red with an asterisk** (`Locations *`) until the
project is saved. A controller in the device list is marked the same
way. This is the one place that shows "what is not on disk yet" without
opening every branch in turn.

The root of the tree carries the project's name — **double-click renames
it in place**, the same field as in [Project
Information](help://info).

## Toolbars

**The top toolbar is fixed** and always acts on **the project**: New,
Open, Save, Save As, Undo, Redo, Help. It works on every branch —
including the ones with no editor at all.

**The contextual toolbar** below it belongs to the active department. In
Screens and Logic those are the editors' own tools, together with the
lifecycle of their own documents.

## F1 — contextual help

At any moment **F1** opens the help on the topic for the branch you are
in. No need to find it in the list.

## Language

**Settings → Language** switches the interface and this help. Keys and
values stored in the project do not change — only what you see does.
