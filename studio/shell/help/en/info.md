# Project Information

Name, author, description, and revision of the current project. This is
also where the whole `projekt.epw` file's own lifecycle lives,
deliberately separate from the fixed New/Open/Save toolbar (that one
still means "the active editor's own document" — a Logic diagram or a
Synoptic screen):

- **New Project** — starts a blank project (asks first if the current
  one has unsaved changes).
- **Open Project...** / **Save Project** / **Save Project As...** —
  operate on the whole `projekt.epw` file (cards, points, apparatus,
  intrusion alarm, protection, Modbus bus).

The **Revision** field increases on every save — the same number Studio
should compare against the controller's own revision before uploading a
project (see "Controller Connection").
