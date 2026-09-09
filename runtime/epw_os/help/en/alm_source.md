# Where Alarms Come From

The Alarms page shows every alarm the program has raised. Currently,
the real (not test) sources of alarms are:

- **Device communication failure** — when any of the four monitored
  devices (see [Device Status Panel](help://mv_device_status)) goes
  into a COMM_FAILURE state.
- **EMERGENCY STOP** — when the emergency-stop tag is active.
- **System health failure** — when the system health monitor
  (safety_kernel) detects an unhealthy device or an unhealthy system
  overall. Details in
  [System Health Monitoring](help://saf_kernel).

An alarm disappears from the active list once its cause clears — but if
it was never acknowledged first, it stays in a state that still
requires acknowledgement. See
[Active vs. Unacknowledged Alarm](help://alm_states).
