# Line Types

Every supervision line is exactly one of four types, chosen when it's
configured:

- **Instant** — raises an alarm the moment it's violated, but only
  while its zone is ARMED. No effect while disarmed or during an
  entry/exit delay.
- **Delayed** — the entry/exit type. Violating it while ARMED starts
  the zone's entry-delay countdown instead of alarming immediately; if
  the zone isn't disarmed before the countdown reaches zero, it alarms.
  No effect while already disarmed.
- **24-Hour** — alarms immediately **regardless of the zone's arming
  state**, including while fully disarmed. For things that should never
  be violated at all — a tamper switch, a protected panel.
- **Supervisory** — signals its violation (visible on the page, and to
  logic — see [Signals for Logic](help://intr_tags)) but **never**
  raises an alarm on a violation, in any zone state. For external
  sensors you want to watch or react to (e.g. lighting control) without
  them being part of the alarm itself. This is specifically about a
  *violation* (motion in front of the sensor) — a *fault* on the same
  line (sabotage, a short, a cut cable) still alarms exactly like every
  other line type; see
  [Input Modes: Contact vs. Parametrized](help://intr_input_modes) for
  what counts as a fault.

A zone's exit delay and entry delay (see
[Arming, Disarming, and Delays](help://intr_arming)) apply to every
Instant/Delayed line in that zone as a whole — while either is
counting down, those two line types are inert; only a 24-Hour line
pierces through in every state.
