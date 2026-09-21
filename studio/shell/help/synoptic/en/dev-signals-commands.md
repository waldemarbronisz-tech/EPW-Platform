# 4.9 Signals and Commands Exposed to Control Logic

Every device exposes a set of signals, commands and - for some behaviors - inhibit signals to EPW-Logic-Studio's control logic, derived ENTIRELY from the behavior field (never separately declared).

| Behavior | Signals (read) | Commands (write) |
| --- | --- | --- |
| SWITCHED | state (open/closed/moving/fault), discrepancy, .COUNTER (if enabled) | OPEN / CLOSE |
| SIGNAL | alarm state | (none) |
| MEASURED | measured value | (none) |
| MODULATED | setpoint, feedback value (if configured) | set value |

Inhibit signals exist so logic can FORBID a command from executing, not only send one. Without them, control logic can TURN a device ON, but cannot BLOCK it from a command the operator sends straight from the screen - the operator's command then goes directly to the output, with no way for a logic interlock to intercept it.
