# What Each Level Can Do — Full Permission Table

The table below describes exactly what the code checks — every one of
these gates runs TWICE: once visually (a disabled button or a
non-editable cell) and once at the moment the action actually executes,
regardless of what the interface showed a moment earlier. This means
dropping to a lower level mid-session (e.g. through the automatic
logout — see [Automatic Logout](help://al_timeout)) always stops the
action, even if the button used to be enabled.

| Action | Required level |
|---|---|
| Viewing every page except Audit Log and Engineer Mode | User |
| Controlling a device from Main View (the one-line diagram) | Operator |
| Acknowledging an alarm (Alarms) | Operator |
| Editing a digital input's description (Digital Inputs) | Engineer |
| Forcing a digital input in simulation mode (Digital Inputs) | Engineer |
| Editing a digital output's description (Control Outputs) | Engineer |
| Editing an analog point's description / unit / technical note (Analog Inputs) | Engineer |
| Adding / removing an analog point (Analog Inputs) | Engineer |
| Full analog point configuration — the Configure button (Analog Inputs) | Engineer |
| Changing protection settings — stage enable, setting, hysteresis, delay, action (Protection Settings) | Engineer |
| Resetting protection statistics (Protection Settings) | Engineer |
| Editing project properties (Project → Project Properties) | Engineer |
| Entering and exiting Kiosk Mode (Settings → Kiosk Mode) | Engineer |
| Viewing the Audit Log page (navigation and content) | Engineer |
| Viewing the Engineer Mode page (protection verification) | Engineer |

## What does NOT require raising your level

- Viewing Main View, Digital Inputs, Control Outputs, Analog Inputs,
  Protection Settings, Power Quality, System Topology, Alarms, Events —
  available to everyone, including User.
- Settings → Language and Screen Sleep — available at every level.
- Exporting historical data and exporting events to CSV — available at
  every level.
- Help (this window) — available at every level, no PIN, including in
  Kiosk Mode.

When the level is too low, the program shows an "Access denied" message
and records the attempt to the audit log — it **never** prompts for a
PIN at that moment. To raise your level, you have to do it deliberately
from the top bar — see
[Changing Level and Entering a PIN](help://al_pin).
