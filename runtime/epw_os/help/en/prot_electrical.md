# Electrical Protections

The classic relay-style settings: **Voltage** (under/over voltage,
neutral overvoltage, phase sequence/loss), **Frequency** (under/over
frequency), **Current** (instantaneous and time overcurrent, negative
sequence, thermal overload, earth fault), and **Power/Supply**
(control/technical/UPS voltage loss). Each function has one or more
**stages**, each with its own Setting, Hysteresis, Delay, and Action
(Disabled/Information/Warning/Trip/Custom Logic).

This page is a **configuration table**, not a live monitor — the
"Actual Value" and "Status" columns are placeholders today, not a real
measurement compared against the setting. These settings are meant to
eventually be pushed to and executed by dedicated protection relay
hardware (ADA01), independent of this computer, the same way a real
switchgear panel's protection relays keep working even if the
supervisory computer goes down. Nothing here currently reads a live
tag or drives an output.

Editing any field, enabling/disabling a stage, and resetting the
Pickups/Trips statistics all require **Engineer** level; viewing the
table needs no particular level.

Earlier versions of this page also listed Environmental (cabinet
temperature/humidity/smoke/water/door/vibration), Communication
(device offline), and System (database/watchdog/config-changed)
categories. These were removed, not moved anywhere — they were the
same kind of placeholder as the "Actual Value" column above, never
bound to a real tag or evaluated against one. Environmental's own
threshold-shaped items didn't fit here either, since real process
thresholds now live on their own page, bound to actual configured
analog points — see [Process Protections](help://prot_process).
