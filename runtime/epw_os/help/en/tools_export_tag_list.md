# Exporting the Signal List (Logic Studio/Synoptic Editor)

**Tools → Export Signal List...** writes every tag currently registered
in this controller to a JSON file - the list Logic Studio and the
Synoptic Editor read to know what actually exists to pick from when
building a program or a screen, instead of guessing at names. Available
at every access level, no PIN - a read-only export, the same "already
visible at User level" reasoning the REST API's own `GET` endpoints
document (see [The REST API](help://api_what)).

If a live connection to a running controller is available instead of a
file, `GET /api/v1/tags/export` returns the exact same structure over
HTTP, unauthenticated (same reasoning as every other read-only REST
endpoint).

## What's in the file

A header:

- `format_version` - the shape of this file itself. Logic Studio
  should refuse to load a version it doesn't recognize rather than
  guess at a shape that may have changed.
- `exported_at` - when this export was taken (UTC).
- `project_name` - the project this came from.
- `epw_os_version` - which EPW OS build produced it.
- `tag_count` - how many tags follow, for a quick sanity check.

Then, for every tag:

- `name` - the exact, full tag name - never changes between EPW OS
  versions or exports (a stable identity Logic Studio/Synoptic Editor
  can save a reference to).
- `data_type` - `BOOL` / `INT` / `REAL` / `STRING`.
- `direction` - `READ_ONLY` or `READ_WRITE`. **Only `System.Theme` is
  `READ_WRITE` today** - it is the one tag a logic program is currently
  allowed to write, to switch the active visual theme (see
  [Visual Themes](help://set_theme)). Every other tag - including ones
  a manager happens to read reactively, like an intrusion zone's own
  arm/disarm input - is `READ_ONLY` in this export; a general-purpose
  family of logic-writable command tags doesn't exist in the code yet
  (see "request_tags" below).
- `module` - a readable label for which part of the controller owns
  this tag (e.g. "Intrusion Alarm System", "Digital Inputs").
- `group` - the tag name's own prefix (e.g. "Security", "DI", "ELA01")
  - use this to build a tree, one branch per group, the same way this
    list's own top-level `groups` object already does (each key is a
    group name, each value the list of tag names in it).
- `description` - if one was ever set.
- `is_simulated` - true for a tag whose current value comes from a
  simulation sandbox, not real hardware or logic (e.g. the Power
  Quality page's sliders) - useful for graying those out or flagging
  them differently in a picker.
- `unit` - only present (non-null) for a configured Analog Input point.
  Every other tag has `unit: null`.
- `value` - the tag's value at the moment of export. Informational only
  - by the time you open the file, it may already be stale; poll
    `GET /api/v1/tags` (or `/tags/{name}`) for a live reading.

`request_tags` is always an empty list today - reserved for a future,
separate family of command tags a logic program will be able to write
to request something (arm a zone, force an output) through a declared,
general-purpose contract. That layer doesn't exist yet; this key exists
so Logic Studio has a stable place to start reading from once it does,
without needing a new file format version for that alone.

## What this export never does

Taking this export never changes anything - it only reads
`TagManager`/the project file, never writes to either. Re-run it as
often as you like.
