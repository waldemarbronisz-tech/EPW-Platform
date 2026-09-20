# MQTT Integration

The controller's link to an MQTT broker (usually Home Assistant). This
is a **project setting**: it travels with the project to the controller,
the panel may change it (Engineer, audited), and differences show up in
[Controller Settings (live)](help://controller).

## Broker

| Field | Meaning |
|---|---|
| **MQTT integration enabled** | the master switch |
| **Broker address / Port** | where to connect |
| **Username** | the account on the broker |
| **TLS** | an encrypted connection |
| **Client id** | the client's identifier on the broker |
| **Topic prefix** | the start of every topic, by default `epw/<controller id>` |
| **Publish interval** | how often to publish state |
| **Default deadband** | how far a value must move before it is worth publishing |
| **Queue limit** | how many messages to hold while the broker is away |

**The password is not here.** It is entered once, on the controller's
panel (Settings → MQTT), and stays there.

## Incoming mappings (topic → `Link.*` tag)

A remote topic feeds a local `Link.<id>.In<n>` tag of the given type. A
value older than **"stale after"** is marked stale rather than pretending
to be fresh.

Rows that came from [Object Links](help://object_links) are marked and
**are removed there**, not here — Studio never touches mappings entered
by hand.

## Per-tag deadbands

A separate table for points that need a different sensitivity from the
default — temperature every 0.1 °C, pressure every 0.01 bar.

## Control from Home Assistant

The link is no longer a view-only one: HAOS can arm and disarm the alarm
system, clear an alarm, silence the sounder, change protection settings
and command apparatus. **Forces are deliberately outside this channel**
— a force is a tool for somebody standing at the cabinet.

Identity travels in the message (a token per person, issued on the panel
— see [Alarm System Users](help://intrusion_users)), because Home
Assistant has one MQTT account and the broker could not tell two people
apart. A refused command looks like a break-in and raises a **silent
alarm**.
