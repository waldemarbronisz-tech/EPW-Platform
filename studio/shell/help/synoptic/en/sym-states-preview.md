# 6.3 Symbol States and the Editor Preview

Every symbol type declares its own list of allowed states (`allowedStates`) and a default state in the registry. Example: the indicator diode has ON/OFF/QUALITY; the meter (SCADA, the static symbol - see [7.1](help://synoptic/elem-meter)) has no state of its own at all.

Since the editor has no live data, the state currently DISPLAYED comes from the object's own `editor.preview_state` field - a manual setting in Properties, used purely to see how the symbol looks in a given state while designing, never a reading from real hardware.
