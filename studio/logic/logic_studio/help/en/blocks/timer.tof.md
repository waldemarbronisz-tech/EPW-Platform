### How it works (off-delay)

```
IN  ______|‾‾‾‾‾‾‾‾‾‾‾‾|______________________________
Q   ______|‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾|__________________
                       |<-- PT --->|
```

- Q becomes TRUE **at once** with IN.
- After IN drops to FALSE, Q holds for another PT ms, then goes out.
- If IN returns to TRUE while the count runs, the count is abandoned -
  Q keeps going and PT counts from the next drop (retriggerable).
- ET counts from the drop of IN (ms, at most PT).

The family: [Timers TON, TOF, TP](help:concept_timers).

### 1. Fan run-on

The fan must run 60 s after the heater is switched off, to cool it:
`Heater running` -> TOF 60000 ms -> `DO fan`.

### 2. Light on a motion sensor

`DI motion sensor` -> TOF 120000 ms -> `DO lighting`. Every new movement
extends the light by a full 2 minutes.

### 3. Stretching a short signal

A counter's pulse lasts one scan - too short for a lamp. TOF 500 ms
stretches it so it can be seen.
