# 4.7 MODULATED - Continuously Controllable Devices

MODULATED is a continuously controllable device: a modulating valve, a VFD. Fields: setpointOutput (an AO channel address - the setpoint sent to the hardware), an optional feedbackInput (an AI channel address - the actual position/speed, if the hardware reports it), unit, rangeMin/rangeMax, startupValue and safeValue (both must fall within rangeMin..rangeMax).

startupValue and safeValue, just like a SWITCHED device's safeState ([4.4](help://synoptic/dev-switched)), belong to the HARDWARE'S OWN CONFIGURATION, not to the screen's logic - they describe what value the device should take on startup and in its safe state.
