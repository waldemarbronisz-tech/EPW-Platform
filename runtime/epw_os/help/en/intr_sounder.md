# The Sounder

This controller **drives no siren**. It publishes the sounder's state,
and the logic program decides which output that reaches — see [What the
Logic Program Can See](help://logic_signals).

That is deliberate. One siren, two sirens, a siren plus a strobe, a
siren through a contactor, a siren that must not sound while the
generator is running — all of that is the same problem, a diagram,
instead of five options in a configuration dialog.

## The four readings

| Signal | Meaning |
|---|---|
| `SEC.SYSTEM.SIREN_ACTIVE` | the sounder should be sounding **right now** — this is what you wire to an output |
| `SEC.SYSTEM.SIREN_TIME_LEFT` | seconds it may still sound for |
| `SEC.SYSTEM.STROBE_ACTIVE` | the light, on from the alarm until the memory is cleared |
| `SEC.SYSTEM.PANIC` | a hold-up line fired and nobody has acknowledged it yet |

The same state is on the tags `Security.System.SirenActive`,
`.StrobeActive` and `.Panic`, so a screen and Home Assistant see it too.

## It stops on its own

`SIREN_ACTIVE` goes false once the configured sounding time is up
(**Studio → Zones → Sounder**; 0 means no limit) **while the alarm
carries on**. A siren that never stops is usually against local noise
rules, and the strobe is what keeps showing that something happened.

## Silence is not disarming

The **Silence** button on the Overview page stops the **noise** and
nothing else: the zone stays in ALARM, the alarm memory stays, the
strobe stays on. "Turn the noise off" and "this is dealt with" are two
different decisions, often minutes apart. The second one is
[clearing the alarm memory](help://intr_alarm_memory).

The button only appears while there is noise to stop, needs Operator
level, and is refused for somebody whose zones do not include the one
that is sounding. Home Assistant can do the same thing over
[MQTT](help://mqtt_commands).

A **new** alarm sounds again even after a silence — somebody silenced
the previous one, and that decision does not cover a fresh break-in.

## The panic line

A **Panic (hold-up)** line alarms in any zone state, night arming
included, and by default **does not sound the siren**: the point of a
hold-up alarm is that the person standing over you does not learn you
pressed it. The alarm itself is entirely real — the memory latches, the
strobe comes on, `PANIC` goes true, everything is logged. An
installation that wants it audible turns that off in Studio.

`PANIC` clears with the alarm memory, not with disarming: it means
"somebody pressed it and nobody has acknowledged that yet".
