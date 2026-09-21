# 7.5 Indicator Diode

The indicator diode is a symbol with three allowed states: ON (lit, a green core), OFF (dark, matte) and QUALITY (yellow - used, among other things, to flag a missing/invalid data source, e.g. a signal panel row pointing at a device that no longer exists - [7.2](help://synoptic/elem-signal-panel)).

The ALARM state color (red) is a separate, third diode color set, used beyond the diode symbol itself - in panels and other places that need to signal an alarm condition, independent of whether that particular diode instance is currently ON/OFF/QUALITY.

The diode's radius has two fixed theme values: a smaller one for diodes on schematic symbols, a larger one in signal and status panels - never a value typed locally in a component.
