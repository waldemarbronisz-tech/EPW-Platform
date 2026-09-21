# 1.2 Place in the EPW Platform

The EPW platform is three separate applications, each in its own repository:

- EPW-OS - the runtime application. Displays screens, reads and writes signals on real hardware, handles alarms, access levels, history.
- EPW-Logic-Studio - builds automation: control rules, interlocks, sequences. That is where, for example, the switch-counter warning threshold is defined (see [4.4](help://synoptic/dev-switched)).
- EPW-Synoptic-Editor (this program) - builds the screen graphics and the device list that EPW-OS then displays and EPW-Logic-Studio consumes in its rules.

EPW-OS's own code (`epw_os/gui/widgets/synoptic_runtime.py`, `epw_os/gui/main_window.py`) mentions Home Assistant as an ADDITIONAL layer - every SWITCHED/SIGNAL/MEASURED/MODULATED device has a `publishToHa` field saying whether its state should also reach Home Assistant as an entity. Home Assistant is not a control path, though: nothing in this editor or in the DeviceSchema contract assumes a command can come back FROM there to a controller - it is a convenience for monitoring/notifications, not a command channel.

> **Note:** A discrepancy found while writing this help: EPW-Logic-Studio, named in this task's own brief as already having a Windows-98-style help system, does NOT actually have one (checked directly in its repository) - only EPW-OS does. Reported in this task's own completion report.
