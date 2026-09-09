# Data Retention

**Settings → Data Retention...** (Engineer level) controls how long two
different kinds of history are kept: Historian's measurement data, and
the audit log's record of who changed what. **Both are off by default —
until you configure a limit, this program behaves exactly as it always
has, and nothing is ever deleted.**

## Why these are two separate settings, not one

**Historian** records tag values over time — a trend of what a
measurement was doing. Old measurements eventually stop being useful,
and on a memory card that only has so much room (this program's target
platform is an Orange Pi, often with an SD card), letting that table
grow forever is not sustainable.

**The audit log** is different: it is the record of *who did what* —
logins, PIN changes, who changed a protection setting and when. Quietly
deleting old audit entries would mean that, a year from now, there is no
way to answer "who changed this protection setting?" That is not the
same problem as an old measurement no longer being interesting, so it
does not get the same solution.

## Historian retention

Set a maximum age (days) and/or a maximum row count — either one, both,
or neither (0 means "unlimited" for that one). Whichever limit is
exceeded, the *oldest* rows are removed first. This runs in the
background, on Historian's own worker thread — it never blocks a tag
write, and it never blocks the interface. Every time rows are purged,
how many and what date range is recorded to the application log and, if
available, the audit log.

## Audit log retention — archive first, always

The audit log can also be given a maximum age and/or row count. The
crucial difference: **before any audit log row is deleted, it is
written to a CSV archive file first — a plain text format any
spreadsheet program can open, no special software needed.** If that
archive write fails for any reason (disk full, folder not writable), **nothing
is deleted** — the database is left exactly as it was. The archive
folder is configurable (Browse... in the dialog); left blank, a
built-in default location next to the database is used.

Once an archive-and-purge cycle succeeds, the audit log itself gets one
new entry recording that it happened — how many rows, what date range,
and which archive file — so the fact that old entries were cleaned out
is never itself invisible.

## Database size

The dialog shows the current database file size and the row count in
every table, so you can judge whether retention is actually needed
before configuring anything. A separate, optional warning threshold (in
MB) shows a status bar indicator once the database file grows past it —
independent of the two retention settings above, since it's about the
whole file, not a per-table limit.
