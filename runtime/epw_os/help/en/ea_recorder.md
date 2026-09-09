# The Event Log

The **Events** page is a live log of operational events: control
actions, alarms, setting changes, faults. Each row has a timestamp,
priority, group, object, event description, user, run mode, and
result.

Rows are color-coded by priority: yellow (WARNING), red (ALARM),
magenta (FAULT), dark red (TRIP), cyan (system events), green
(everything else).

## Filtering and Searching

The text field above the table searches every column at once. The
Group dropdown narrows the view to one category (PROTECTION, OPERATION,
AUTOMATION, ENVIRONMENT, SYSTEM). Clicking a column header sorts by it
(clicking again cycles: ascending, descending, back to the default
time-based sort).

**Important**: this log exists only in the program's memory — it is not
written to the database and disappears when the program closes (unless
exported first). This is the key difference from the audit log — see
[The Audit Log and How It Differs from the Event Log](help://ea_audit_log).

It also keeps only the most recent **5000** events during a single
run — once that many have appeared, the oldest ones quietly drop off
as new ones arrive, so the page stays responsive on a system left
running for a long time. Export to CSV first if older entries need to
be kept.
