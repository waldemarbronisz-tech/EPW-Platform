# Training Mode

**Settings > Training Mode** — a checkbox, visible and usable only at
the **Engineer** level. While checked, the entire program works exactly
as normal, but no command actually reaches a driver, so nothing on real
hardware can ever switch. It exists for learning the interface and
demonstrating the system with zero risk of actually operating anything.

## Why this exists

Today, the only thing standing between an operator and real hardware is
that the drivers happen to be simulated. Once a real driver is
connected, that accidental safety net is gone. Training Mode is that
same protection, made explicit and independent of which driver is
configured — it works identically whether the driver behind it is
`SIM_DRIVER` or a real one.

## What actually changes

Nothing about how a command is decided. A command still goes through
the complete normal path — the access-level check, interlocks, the
Command Manager, the platform's own safety checks — with no shortcuts
and no exceptions. It is still visible in the Event Log exactly as any
other command would be.

The only difference is at the very last step: instead of reaching the
driver layer, the command is quietly stopped right at its boundary.
Feedback is still simulated realistically, so a device still visibly
"changes state" on screen — the interface behaves exactly as if the
command had gone through for real. What never happens is any actual
write to hardware.

## What stays exactly the same

Permissions and interlocks work identically whether Training Mode is on
or off. A command blocked by an interlock, an insufficient access
level, or the platform's own safety checks is blocked in Training Mode
exactly as it would be otherwise — Training Mode changes nothing about
what is *allowed*, only whether an allowed command physically reaches
hardware.

## The indicator — impossible to miss

Whenever Training Mode is active, the status bar shows a clearly
colored warning label, and the whole main workspace gets a colored
border. Both appear together specifically so the mode can never go
unnoticed — nobody should ever believe they are controlling real
equipment while actually in Training Mode.

## Turning it on and off

Every time Training Mode is turned on or off, that change is recorded
in the [Audit Log](help://ea_audit_log) — who changed it and when.

Training Mode is **never remembered between program restarts**. The
program always starts up in normal mode; turning Training Mode on has
to be done again, deliberately, every session.
