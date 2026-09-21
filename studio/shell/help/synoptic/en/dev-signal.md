# 4.5 SIGNAL - Signalling-Only Devices

SIGNAL is a signalling-only device, with no command output: an indicator lamp, an auxiliary contact used as a sensor, a limit switch reporting state with no way to control it from the screen.

Fields: feedback.di (one digital input) with optional invert, alarmState (HIGH or LOW - which signal LEVEL counts as alarm) and debounceMs (anti-chatter delay, >= 0).

Unlike SWITCHED, SIGNAL has no command field at all - nothing can be sent from it to the hardware. That is deliberate: SIGNAL exists to SHOW something, never to CONTROL something.
