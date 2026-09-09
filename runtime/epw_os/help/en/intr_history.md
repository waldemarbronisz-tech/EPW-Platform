# Alarm Event History

A complete, chronological record of everything the intrusion alarm
system has done — on its own page, Event History, separate
from both the Event Recorder (every process/alarm event across the
whole program) and the Audit Log (every security/configuration action
across the whole program, not specific to this module).

**What's recorded**: arming and disarming (who, when, which zone), every
line violation (which line, what state the zone was in), every alarm —
with its [first cause](help://intr_alarm_memory) marked — every line
and power fault, bypassing a line and un-bypassing it, a line marked
Suspect, walk-test mode starting and ending, and an alarm memory being
cleared.

**Filtering**: by zone, by event type, and by date range, from the
toolbar above the table — pick what you want and press *Apply Filters*.
Filtering needs an explicit button here (unlike the live zone/line
tables above it) because re-querying on every single event, the moment
it happens, would be wasted work for a view most people open to look
back at something, not to watch live.

**Exporting**: *Export CSV* saves exactly what's currently on screen —
apply your filters first, then export, the same as the CSV export on
every other page in this program.

**Retention** (Engineer level, *Configure Retention*): a maximum number
of events, a maximum age in days, or both — either left at 0 means no
limit on that one. The oldest events are deleted automatically once a
limit is exceeded, so this history can't grow forever on a device with
limited storage (an Orange Pi's SD card, for instance).
