# 7.2 Signal Panel

A signal panel is the same mechanism as the meter ([7.1](help://synoptic/elem-meter)), except every row ends in a two-state DIODE instead of a value field. A row either points at a device, or is a manual row with its own diode state set directly (ON/OFF/QUALITY).

The panel wizard shows SIGNAL and SWITCHED devices, grouped by LOCATION (not by unit, unlike the meter wizard) - MEASURED never appears here, since it has no "closed/open" notion for a diode to signal.

A row pointing at a valid SIGNAL/SWITCHED device always previews its diode as ON - a manual design-time preview (the editor has no live data), not a reading of a real contact's state. A row pointing at a device that does not exist, or that has a different behavior (e.g. MEASURED), shows the QUALITY diode instead of throwing an exception.
