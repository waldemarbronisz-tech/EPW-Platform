# Controlling Devices and Required Permissions

Controlling a device from Main View requires the **Operator** level.

## Control sequence

1. Click a device on the diagram (Q1, KMG, KM1, or KM2).
2. A window appears showing the device's current state and an
   **Interlock** row — whether the command opposite to the current
   state is currently permitted. If the program's logic blocks the
   command, the corresponding action button (OPEN/CLOSE) is disabled,
   and the reason is spelled out.
3. Choose OPEN or CLOSE (only the action opposite the current state is
   available).
4. A confirmation window appears — only confirming it actually sends
   the command. Permissions are checked again at this point, in case
   they lapsed while these windows were open.
5. The device shows a "pending" state, then shortly after, its feedback
   state.

## What blocks control

Before a command is sent, the program checks, in order:

- whether EMERGENCY STOP is active;
- whether the target device is in a communication-failure state;
- whether the overall system health is fine — see
  [System Health Monitoring](help://saf_kernel);
- the control logic's own rules (if a logic project is loaded).

If no control logic project is configured at all, that's a normal
state — manual control still works. Only a logic project that IS
configured but fails to load is treated as an actual fault that blocks
commands.
