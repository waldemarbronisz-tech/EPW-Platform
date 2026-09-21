# The Signal Panel Wizard Does Not Show an Expected Device

SYMPTOM: an expected device does not appear in the signal panel wizard's list.

CAUSE: that wizard shows only SIGNAL and SWITCHED devices ([7.2](help://synoptic/elem-signal-panel)) - MEASURED and MODULATED never appear here, since they have no two-state notion for a diode to signal.

FIX: check that device's behavior in the Device List - if it is MEASURED, it belongs on a meter ([7.1](help://synoptic/elem-meter)), not a signal panel.
