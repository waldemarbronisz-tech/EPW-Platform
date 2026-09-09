# First Cause and Alarm Memory

When a zone alarms, the system remembers exactly which line triggered
it first, and keeps that record visible until someone clears it — even
after the zone is disarmed.

**First cause** — the line and the exact time that started the current
alarm. If several lines trip in quick succession (someone walking
through the premises), every one after the first is recorded too, but
kept clearly separate — as *further alarms*, never merged into one
list with the first cause. This is what tells you which way someone
actually came in.

**Alarm memory** — once a zone has alarmed, its memory stays **active**
until it's explicitly cleared, no matter what happens to the zone in
the meantime: disarming it, re-arming it, even a full restart of the
program. This is the same principle the safety-kernel latch already
uses elsewhere in this program — an event that happened stays on
record; it doesn't quietly vanish just because the immediate danger
passed. The zone's row shows an "alarm memory" note while this is
active, and the **Alarm Memory** button (toolbar, above the zone list)
opens the full picture for any zone: whether it's active, the first
cause with its line and time, and the list of anything that alarmed
afterward.

**Clearing it** — Operator level or higher, from the Alarm Memory
dialog's own Clear button. Clearing is recorded to the audit log and to
the [alarm event history](help://intr_history). Once cleared, the next
alarm (whenever it happens) starts a fresh record — its own first
cause, its own list.

Nothing about arming, disarming, or how a zone actually reaches ALARM
changes because of this — see
[Arming, Disarming, and Delays](help://intr_arming). This only affects
what's *remembered* about an alarm that already happened.
