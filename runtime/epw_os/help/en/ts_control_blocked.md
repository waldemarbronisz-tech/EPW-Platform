# Control Is Blocked

When the device control window (Main View) or the Force button (Control
Outputs) shows that a command isn't allowed, the reason is always one
of the following — the program spells it out directly in the window:

1. **EMERGENCY STOP is active** — the emergency stop blocks every
   command until it's cleared.
2. **The target device is in a COMM_FAILURE state** — see
   [A Device Shows OFFLINE](help://ts_device_offline).
3. **The system is in an unhealthy state** — the system health monitor
   (safety_kernel) has detected a problem with a device or the system.
   See [System Health Monitoring](help://saf_kernel) — commands come
   back on their own once system health returns to normal (the alarm
   latch still needs to be acknowledged separately on the Alarms page).
4. **A control logic rule** — if a logic program is loaded for the
   project, its interlock rules may block a specific command. No logic
   program being loaded at all is **not** treated as a fault — that's a
   normal state, and manual control still works in that case.

This is NOT a matter of access level — not even Engineer bypasses any
of these conditions. If the reason for a block doesn't match any of the
above, that's worth reporting as something this help page doesn't
describe yet.
