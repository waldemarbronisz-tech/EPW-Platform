# MQTT Integration

The controller's link to an MQTT broker (Home Assistant): address,
port, username, TLS, client id, topic prefix, publish interval,
deadbands and incoming mappings (remote topic → local
`Link.<id>.In<n>` tag).

**A project setting, not one controller's setting.** The broker and
topics belong to the installation - a replacement controller gets them
with the project. The panel may change them (Engineer, audited,
revision +1 "panel"), and the difference between project and
controller shows in Controller → Controller Settings (live), where it
can be taken with one button, like a protection threshold.

**The broker password is not in the project.** It is entered once on
the panel (Settings → MQTT) and stays in the controller's local file -
the same rule as for PINs and API tokens.

Settings that STAY local (not in the project, because they describe
this controller, not the installation): UI language, REST address and
port, historian, audit and alarm history retention, the database size
warning, the I/O driver. They are shown read-only in Controller →
Controller-local Settings.
