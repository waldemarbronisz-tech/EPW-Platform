# Presentation Mode scenarios

Any `*.json` file in this directory shows up in Tools > Presentation
Mode's scenario list. See `epw_os/core/presentation_mode.py` for the
loader (`load_scenario()`/`PresentationStep`) - this file just documents
the format for anyone writing a new one.

```json
{
  "name": "Display name shown in the picker",
  "description": "One or two sentences, shown when the scenario is selected.",
  "command_definitions": {
    "DEMO_XYZ.CLOSE": {
      "driver_id": "SIM_DRIVER", "output_tag": "Demo.Xyz.CmdSent", "output_value": true,
      "feedback_tag": "Demo.Xyz.Feedback", "feedback_value": true, "timeout_ms": 2500
    }
  },
  "steps": [
    {"time_s": 0, "type": "tag", "tag": "Meas.L1", "value": 230.1, "quality": "SIMULATED", "description": "..."},
    {"time_s": 5, "type": "command", "target": "DO02", "action": "OPEN", "description": "..."},
    {"time_s": 8, "type": "alarm", "alarm_id": "DEMO_XYZ", "message": "...", "priority": 3, "source_tag": "Meas.L1", "description": "..."},
    {"time_s": 12, "type": "alarm_clear", "alarm_id": "DEMO_XYZ", "description": "..."},
    {"time_s": 14, "type": "device_comm", "target": "Modbus", "action": "SUSPEND", "description": "..."},
    {"time_s": 20, "type": "device_comm", "target": "Modbus", "action": "RESUME", "description": "..."},
    {"time_s": 22, "type": "counter_threshold", "target": "DI1", "value": 3, "description": "..."}
  ]
}
```

`time_s` is seconds from scenario start (not from the previous step) -
steps are re-sorted by this at load time regardless of the order
they're written in the file. `description` is shown in the presentation
dialog's step log; it isn't shown to the audience, so it can be as
technical as you like.

Six step types:

- **`tag`** - `tag_manager.update_tag(tag, value, quality)`. `quality`
  is optional and defaults to `"SIMULATED"` - a presentation step is,
  by definition, a staged value, not a real reading (same convention
  the rest of EPW OS uses to mark simulated data).
- **`command`** - `command_manager.request_command_ex(target, action)` -
  the exact same dispatch path a real Force button uses (full
  safety_kernel/logic_engine validation; GRANICE forbids a scenario
  bypassing either). `action` is whatever the target's command
  definitions actually support - `"OPEN"`/`"CLOSE"` for the built-in
  DO01-DO64 channels, or whatever your own `command_definitions` (below)
  define.
- **`alarm`** - `alarm_manager.trigger_alarm(alarm_id, message,
  source_tag, priority)`. Use an `alarm_id` prefixed `DEMO_` (see the
  sample scenario) so it's obviously not a real device-comm-failure/
  EMERGENCY_STOP alarm id if it ever shows up in a screenshot.
- **`alarm_clear`** - `alarm_manager.clear_alarm(alarm_id)`. Optional -
  any alarm a scenario triggers and never explicitly clears is cleared
  automatically when the presentation stops (Task: "zatrzymanie
  przywraca stan sprzed uruchomienia").
- **`device_comm`** - `target` is a device id (e.g. `"Modbus"`,
  `"OrangePi"` - see `device_manager.devices`), `action` is
  `"SUSPEND"`/`"RESUME"`. Tells the driver actually servicing that
  device to stop/resume reporting its comm heartbeat - a real device
  that stopped answering, not a faked status tag, so SafetyKernel's own
  3-missed-cycle detection genuinely fires on its own schedule. A
  driver that doesn't implement this (see `BaseDriver.set_comm_suspended()`)
  just ignores it.
- **`counter_threshold`** - `target` is a DI tag name (e.g. `"DI1"`),
  `value` is the new switching-counter warning threshold (an integer,
  or `null` to clear it). Calls the same
  `SwitchingCounterManager.set_warning_threshold()` the Digital Inputs
  page's own Engineer-only control uses - handy for a short demo that
  can't wait for a real installation's real threshold. Restored to its
  pre-scenario value when the presentation stops, along with every
  other counter field for that tag.

A step with a bad/unknown value is skipped with a logged warning, not a
crash that aborts the rest of the demo - check the log if a step didn't
seem to do anything.

## `command_definitions` (optional)

A scenario may declare its own command definitions, in exactly the
shape `CommandManager.load_definitions()` already takes (see
`command_not_confirmed.json`). Merged in when the scenario starts,
under keys of your own choosing - use a target name that doesn't
collide with a real device (e.g. `DEMO_XYZ`, never `DO01`-`DO64`), so a
demo-only definition never overwrites a real one. Any `output_tag`/
`feedback_tag` named here that doesn't already exist is auto-registered
as a scratch tag - useful for building a demo command whose
`output_tag` differs from its `feedback_tag`, the only way to get a
command that genuinely never confirms (every built-in DO01-DO64
definition is self-referential - output_tag == feedback_tag - so it
always confirms instantly under Training Mode; there's no way to make
a *real* device's own default command hang without one of these).

## Shipped scenarios

- **`voltage_sag_trip.json`** - normal operation -> a voltage sag on L1
  -> an undervoltage alarm -> a protective trip -> recovery.
- **`normal_operation_manual_control.json`** - the simplest: a device
  closes and opens on command, with real feedback confirmation and an
  event-log entry. Shows the permission path and the command pipeline.
- **`communication_loss_and_latch.json`** - a device stops answering;
  SafetyKernel's real 3-missed-cycle detection fires; communication
  returns but the fault latch stays set until manually acknowledged.
- **`overload_ramp_trip.json`** - current climbs gradually (visible on
  the Trends page), crosses a warning then a trip threshold, an alarm
  fires, the breaker opens.
- **`command_not_confirmed.json`** - a command is sent but its
  feedback never arrives; the real command-supervision timeout fires
  and the device is never shown as closed.
- **`mechanical_wear_and_service_history.json`** - a series of
  switching cycles crosses a (temporarily lowered) counter warning
  threshold - the natural point to show Service History live.
