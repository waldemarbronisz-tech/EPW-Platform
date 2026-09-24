### How it works (on-delay)

```
IN  ‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾___________
Q   ___________|‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾___________
    |<-- PT -->|
```

- Q becomes TRUE once IN has been TRUE **without a break** for PT ms.
- Any drop of IN to FALSE clears Q and the time at once - the count
  starts over on the next rise of IN.
- ET shows the elapsed time (ms, at most PT).
- The time: the PT pin (when connected) wins over the "Preset (ms)"
  property.

The family: [Timers TON, TOF, TP](help:concept_timers).

### 1. Contact debounce / a stable confirmation

A gate's limit switch chatters while closing. `DI limit` -> TON 300 ms ->
"gate closed": the signal must be stable for 0.3 s before the logic
accepts it.

### 2. Supervising a command

After a CLOSE command the apparatus has 2 s to confirm: `Command` AND NOT
`Feedback` -> TON 2000 ms -> `M.BRAK_POTWIERDZENIA` -> alarm. When the
feedback arrives in time, the TON input drops and no alarm is raised.

### 3. A start-up sequence

The circulation pump first, the boiler 5 s later: `Start` -> TON 5000 ms
-> boiler permission. Several TONs with growing times from one start
signal make a simple timed sequence.
