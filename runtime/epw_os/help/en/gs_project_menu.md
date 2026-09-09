# The Project Menu

**Project → Project Properties...** opens a window with two parts:

- **Editable fields** — Name, Description, Location, Author. Viewing
  is open to every level; editing and Save require **Engineer** (the
  fields go read-only and Save is disabled below that level, and the
  check is re-verified again at the moment you click Save, in case
  your level dropped while the window was still open).
- **A read-only summary**, computed fresh from the current project
  every time the window opens — not stored anywhere itself: number of
  analog points, number of digital inputs/outputs with a non-empty
  description, the configured logic project file (or "not configured"),
  and the full path of the active project file. Created/modified
  timestamps are shown next to the editable fields; Modified updates on
  every Save, from any menu item that saves the project, not only from
  this window.

Saving here is recorded to the [Audit Log](help://ea_audit_log).

**Project → Recently Opened** — see [The File Menu](help://gs_file_menu),
which covers it together with New/Open/Save/Import/Export since they
all manipulate the same project file.
