# The Audit Log and How It Differs from the Event Log

The **Audit Log** page requires the **Engineer** level — both to enter
it and to see its content.

## How it differs from the event log (Events)

| | Event Log (Events) | Audit Log |
|---|---|---|
| Content | operational events: control actions, alarms, setting changes | security/configuration events: logins, PIN changes, project property changes, access denials, kiosk mode entry/exit |
| Persistence | memory only, disappears when the program closes | written to the database, permanent |
| Who can view it | every level | Engineer only |

Every entry has a timestamp, event type, who triggered it, a
description, and a result (OK/FAILED) — e.g. a failed login attempt
shows up here as FAILED, even if it never appears in the event log at
all.

The audit log records, among other things: login attempts, PIN changes,
language changes, project property changes, kiosk mode entry and exit,
and every "Access denied" occurrence.
