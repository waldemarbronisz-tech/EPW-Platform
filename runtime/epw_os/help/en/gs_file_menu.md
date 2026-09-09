# The File Menu

Available at every access level, no PIN — these are project-file
operations, not security-sensitive actions.

- **New** — resets to a blank, empty project. Nothing is written to
  disk until you Save; until then it shows as unsaved.
- **Open...** — loads a project file you pick, replacing the current
  one. The loaded file becomes the active project (further Saves go
  back to it).
- **Save** — writes the current project to its active file.
- **Save As...** — writes the current project to a file you pick, and
  that file becomes the new active project (further Saves go there,
  not to the old file).
- **Export...** — writes a standalone backup copy of the current
  project to a file you pick. Unlike Save As, the active project file
  does not change — you keep working on the same file as before.
- **Import...** — loads a file you pick and immediately saves its
  content into the *current* active project file. Unlike Open, the
  active file path does not move to the imported file — Import
  overwrites the project you already had open, in place.

New, Open, and Import all ask for confirmation first if the current
project has unsaved changes, so a careless click can't silently
discard work.

## Recently Opened

**Project → Recently Opened** lists the last project files you've had
open (via Open, Save As, or a previous entry in this same list). A
file that no longer exists at its saved location is shown grayed out
and marked, not silently skipped. **Clear** empties the list.

See also: [The Project Menu](help://gs_project_menu).
