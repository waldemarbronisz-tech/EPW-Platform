# Signals for Logic (Security.* Tags)

The Intrusion Alarm System never controls a siren, light, or
notification itself — it only publishes state as ordinary tags, so the
logic program can react however the installation needs. All of them
start with `Security.`:

**Per zone** (`<id>` is the zone's internal id, e.g. `Z1` — shown next
to its name on the Configure Zones dialog):
- `Security.Zone.<id>.State` — DISARMED / EXIT_DELAY / ARMED /
  ENTRY_DELAY / ALARM
- `Security.Zone.<id>.ArmRequest` — **write** True to arm, False to
  disarm this zone from logic (a key switch, a remote, or anything
  else that can write a tag)
- `Security.Zone.<id>.CountdownRemaining` — seconds left in an exit/
  entry countdown, 0 otherwise
- `Security.Zone.<id>.AlarmMemoryActive` — True while an alarm has
  occurred in this zone since the last explicit clear — see
  [First Cause and Alarm Memory](help://intr_alarm_memory)
- `Security.Zone.<id>.AlarmMemoryFirstCauseLine` — the id of the line
  that first raised the currently-remembered alarm, empty when
  AlarmMemoryActive is False
- `Security.Zone.<id>.WalkTestActive` — True while
  [walk-test mode](help://intr_walk_test) is running on this zone

**Per supervision line** (`<id>` e.g. `L1`):
- `Security.Line.<id>.Violated` — this line's current violated state
  (after minimum-violation-time filtering, if configured — see
  [False-Alarm Filtering](help://intr_filters))
- `Security.Line.<id>.MultiplicityCounting` — True while a violation
  count is running, waiting either for more violations or for the
  window to elapse
- `Security.Line.<id>.Locked` — True while this line is auto-locked
  after repeated alarms this arm cycle
- `Security.Line.<id>.State` — this line's full state: Secure /
  Violated / Tamper / Short / FaultOpen / Undetermined (a Contact-mode
  line only ever reads Secure or Violated — see
  [Input Modes](help://intr_input_modes))
- `Security.Line.<id>.Fault` — True while the line is in any fault
  state (Tamper / Short / FaultOpen / Undetermined)
- `Security.Line.<id>.Suspect` — True while the line has gone longer
  than its configured silence threshold without a violation — see
  [Line Life and Silence Detection](help://intr_line_life)

**System-wide:**
- `Security.System.State` — the same 5 values, aggregated across every
  zone (a single zone in ALARM makes this ALARM too, and so on down in
  urgency)
- `Security.System.Alarm` — True while any zone is in ALARM
- `Security.System.EntryCountdownActive` / `.ExitCountdownActive` — True
  while any zone is counting down that delay (for a buzzer)
- `Security.Supervisory.Violated` — True while any Supervisory-type
  line anywhere is violated (for lighting or similar logic that should
  react to those sensors without being part of the alarm itself)
- `Security.System.LineFault` — True while any supervision line
  anywhere is in a fault state
- `Security.Power.MainsOk` / `Security.Power.BatteryOk` — the two
  independent, optional power checks. **True means healthy** (the
  platform-wide convention: a healthy signal reads high, so a severed
  cable or a dead module fails low and looks like a fault, not like a
  normal state) — False only while that input is actually configured
  AND reads unhealthy; unconfigured reads True (nothing to report,
  same as if the check didn't exist) — see
  [Power Supervision](help://intr_power_supervision)
- `Security.System.TechnicalAlarm` — True while either power check
  above is NOT healthy (`MainsOk` or `BatteryOk` is False); a separate
  category from `Security.System.Alarm`, which stays strictly about
  intrusion/break-in

Writing `Security.Zone.<id>.ArmRequest` is the only tag this system
reads as an input — every other tag above is read-only, written by the
system itself.
