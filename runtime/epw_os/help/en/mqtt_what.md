# MQTT Integration

**Settings → MQTT...** (Engineer level) publishes this controller's
state to an MQTT broker, so Home Assistant or another EPW controller
can consume it without polling the REST API. Disabled by default —
turning it on never changes how anything else in this program behaves.

## The one hard rule: publish-only

This integration **can never receive a command**. It publishes tag
values, alarms, and events outward, and it can be told to read one
other controller's data inward (see "Incoming Link signals" below) —
that is the complete list of what it does. There is no way, today or
ever through this screen, to arm a zone, disarm it, force an output, or
change a setpoint over MQTT. Building that would need its own
authentication/authorization design, the same way the REST API's own
bearer-token scheme was built as its own task after a real
command-bypass vulnerability was found there — it is not something an
integration task adds on the side.

## Configuration

Broker host/port, an optional username, TLS on/off, a client id
(defaults to the project id), a topic prefix (defaults to
`epw/<client id>`), and, for numeric (analog) tags specifically, a
publish interval and a deadband (a value only republishes once it has
both waited that long AND changed by more than that threshold — the
same idea as the Historian's own write deadband, just a separate,
independently-tunable filter for this one destination).

**The broker password is never stored in the project file or the
repository.** It lives in its own local file
(`epw_os/config/mqtt.local.json`), the same "never in project.json"
rule the access-control PINs and the REST API tokens already follow —
though unlike those two, a broker password can't be one-way-hashed
(this program has to send it to the broker, in the clear, on every
connection), so this one file holds the real value, not a hash.

## What gets published

Every tag registered in TagManager, on every value change, as its own
retained topic — a client connecting after startup sees the current
state immediately, not just future changes. Alarms (raised/cleared/
acknowledged) and Intrusion Alarm System events (armed, disarmed,
alarm, line fault) publish too, as short-lived event messages (not
retained — an event is a moment, not a state). Controller status
(online/offline, run mode, version) is retained, backed by an MQTT
**Last Will and Testament**: if this program disappears without a
clean shutdown, the broker itself announces it offline — subscribers
never see a frozen, stale "still fine" reading.

**Simulated data is marked, not hidden.** Every tag also publishes a
sibling "quality" topic (`GOOD`, `SIMULATED`, `STALE`, ...) — the exact
same quality TagManager already tracks for every reading, so a value
with no real sensor behind it (see [Signal Export](help://tools_export_tag_list)
for the same distinction) is never mistaken for a measurement by
whatever is listening on the other end.

Where it can be done automatically, a Home Assistant discovery message
publishes alongside a tag's first value, so it appears as an entity in
Home Assistant with no manual YAML configuration needed there.

## Incoming Link signals (Link.\*)

The **only** thing this integration is allowed to receive: a manually
configured list of *(remote MQTT topic → local tag name)* mappings, the
local name always shaped `Link.<identifier>.In<name>`. Each becomes an
ordinary, read-only-to-everything-else tag your logic program can read
— exactly like an Analog Input, never a command trigger. Configure the
mapping (and how long it may go without an update before it counts as
stale) in the same Settings → MQTT... dialog.

**A mapping with no update for longer than its own configured time is
marked STALE**, not left holding its last value forever — the same
principle device communication supervision already uses elsewhere in
this program: a silent network is not the same thing as "nothing
changed".

## What losing the connection does — and does not — do

Publishing never blocks the program. A disconnected or unreachable
broker cannot slow down or affect logic, alarms, or control in any
way — the worst case is a bounded, in-memory queue of not-yet-sent
messages, which drops its OLDEST entries first once it's full rather
than growing without limit. Reconnection is automatic, with a growing
delay between attempts so a broker that's down for a while isn't
flooded with retries the moment it comes back. If the `paho-mqtt`
library isn't installed at all, or no broker is reachable, the rest of
the program starts and runs completely normally either way — the
integration simply stays inactive, with its connection state visible
right there in the Settings → MQTT... dialog.
