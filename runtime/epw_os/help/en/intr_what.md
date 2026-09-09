# What the Intrusion Alarm System Is

A separate feature from the [Alarms](help://alm_source) page. Alarms
there are **process** alarms — device communication failure, EMERGENCY
STOP — conditions about the plant itself, active regardless of any
"armed" concept.

The Intrusion Alarm System is a burglar-alarm panel: it watches a set of
sensors (**supervision lines**), grouped into **zones** you arm and
disarm, and it raises an alarm when a line is violated under the wrong
circumstances for its type. It never controls a siren, a light, or
sends any notification itself — what happens on an alarm is entirely up
to the logic program running underneath, built on the tags this system
publishes (see [Signals for Logic](help://intr_tags)).

Reach it from **System Alarmowy** in the left navigation - three
separate pages, split by who they're for and how often they're used:

- **Overview** - day-to-day work: arming/disarming, bypass, alarm
  memory, walk test. No configuration fields at all. Viewing is open
  to everyone; arming/disarming needs Operator level or higher.
- **Event History** - the same filterable, exportable event log as
  before, now its own page rather than a tab.
- **Configuration** - installer-only setup: zones/lines, input modes,
  false-alarm filters, power supervision, history retention. The
  whole page requires Engineer level to use, not just individual
  buttons within it.

Every other help topic in this section still describes exactly how
zones/lines/filters/arming work - only WHICH of the three pages hosts
each control changed, not the underlying behavior. The system-wide
state also always shows in the status bar at the bottom of the window,
so it's visible from every page, not just these three.
