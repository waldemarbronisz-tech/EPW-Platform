# Service Notes

The devices' service logbook: "what was done" entries (contact set
replaced, pitting visible), typed on the controller's panel by an
Operator or higher. They complement the switching counters, which say
"how many times / how long".

**Entries are never edited or deleted** - a logbook, not a notepad; a
mistake is corrected with another entry. Studio only shows them.

Since 2026-09-18 the notes are part of the project: every entry added
on the panel is written to `projekt.epw` (revision +1 "panel"), so the
installation's history travels with the project. They reach Studio
through "Receive from Device" or "Take Controller Values" (Controller →
Controller Settings (live) lists them as a `service_notes/<device>/notes`
difference).

Note: sending a project with fewer entries than the controller has
overwrites its logbook - the Controller panel shows that difference
before sending.
