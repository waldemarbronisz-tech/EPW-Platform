### How it works (a pulse of fixed length)

```
IN  ____|‾‾|______|‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾|______
Q   ____|‾‾‾‾‾‾‾|_|‾‾‾‾‾‾‾|_______________
        |<-PT->|  |<-PT->|
```

- A rising edge of IN starts a Q pulse of **exactly** PT, whatever IN does
  afterwards - shorter or longer.
- While the pulse runs, further edges of IN are **ignored** (the pulse is
  neither extended nor restarted).
- ET counts from the start of the pulse.

The family: [Timers TON, TOF, TP](help:concept_timers).

### 1. A coil pulse

A bistable relay or a contactor with an impulse coil needs a pulse of a
set length: `Command` -> TP 200 ms -> `DO CLOSE coil`. The operator may
hold the button as long as they like - the coil gets 200 ms.

### 2. A sound on an event

A short sound on every new alarm: `New alarm` -> TP 1500 ms -> `DO
buzzer`.

### 3. Protection against too frequent starts

A TP of 30 s fired from the start command, its Q (negated) as a condition
of the next start's permission: a second start earlier than 30 s is
refused.
