# What the Logic Program Can See

Beyond the plain point addresses of this project (`ELA1.DI.1`,
`ADA1.DO.3` and the analog points with their engineering values), a
program can read and write these.

## Internal and retentive bits

`M.` bits are the program's own scratch space. `MR.` / `MWR.` bits are
the same thing except they **survive a restart**: their values are kept
in the controller's own state file and come back when the controller
starts again — but only for the identifiers the current program still
declares as retentive. A value left behind by a program that no longer
knows about it is not resurrected.

## System signals (`SYS.*`)

The controller's own state, as signals: whether communications are
healthy, the current access level, whether Training Mode is active,
whether the clock is synchronised, plus pulse and blink generators for
timing things without building a timer chain.

## Alarm system signals (`SSWIN.*`)

The whole intrusion alarm, as signals a diagram can use.

**Reads:** `ARMED` (every zone armed, fully), `ARMED_PARTIAL` (some
zones, or night arming), `DISARMED`, `READY_TO_ARM`, `EXIT_DELAY`,
`ENTRY_DELAY`, `DELAY_REMAINING`, `ALARM_ACTIVE`, `ALARM_LATCHED`,
`ALARM_MEMORY`, `TAMPER`, `FAULT`, `LAST_TRIGGER`, `ACTIVE_COUNT`, and
the sounder's own `SIREN_ACTIVE`, `SIREN_TIME_LEFT`, `STROBE_ACTIVE`,
`PANIC` — see [The Sounder](help://intr_sounder).

**Commands:** `CMD_ARM`, `CMD_ARM_PARTIAL` (night), `CMD_DISARM`,
`CMD_RESET`, `CMD_SILENCE`. They act on **every zone** — the catalogue's
commands have no zone to name — and they execute on a **rising edge**,
so a block holding the signal high does not repeat the command every
scan.

A command also checks the access level the **block itself** declares.
Logic Studio only records that level; this controller is what enforces
it.

## Why the siren is not in this list

Because it is not a signal this controller drives — it is one you wire.
`SSWIN.SIREN_ACTIVE` says the sounder should be sounding; which output
that reaches, through which interlocks, is a line of your diagram. See
[The Sounder](help://intr_sounder).
