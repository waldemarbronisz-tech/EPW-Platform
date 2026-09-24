# Timers TON, TOF, TP

The three timers answer three questions about time: **after how long** to
switch on (TON), **how much longer** to hold after switching off (TOF) and
**for how long** to switch on regardless of the input (TP). All have the
same pins: IN (start/condition), PT (time in ms - the pin wins over the
"Preset (ms)" property), Q (output) and ET (elapsed time in ms, never
more than PT).

Time comes from the engine's clock: in simulation a deterministic
simulation clock (one step = the scan period), on the controller a
monotonic clock. The resolution is one scan - a 300 ms timer at a 100 ms
scan fires after 3 scans.

## TON - on-delay ([block page](help:block:timer.ton))

```
IN  ‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾___________
Q   ___________|‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾___________
    |<-- PT -->|
```

Q = TRUE once IN has lasted PT without a break. A drop of IN clears Q and
the time at once. Typical: contact debounce, "did the feedback arrive in
time" supervision, a start-up sequence, a delayed alarm.

## TOF - off-delay ([block page](help:block:timer.tof))

```
IN  ______|‾‾‾‾‾‾‾‾‾‾‾‾|______________________________
Q   ______|‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾|__________________
                       |<-- PT --->|
```

Q = TRUE at once with IN and for another PT after its drop. A return of
IN during the count extends Q (the count starts over at the next drop).
Typical: fan run-on, light on a motion sensor, stretching a short pulse.

## TP - pulse ([block page](help:block:timer.tp))

```
IN  ____|‾‾|______|‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾|______
Q   ____|‾‾‾‾‾‾‾|_|‾‾‾‾‾‾‾|_______________
        |<-PT->|  |<-PT->|
```

A rising edge of IN gives a Q pulse of exactly PT, however long IN
lasts. During the pulse new edges are ignored. Typical: a coil pulse, a
sound signal, a lock-out against too frequent starts.

## Three traps

1. **PT from the pin versus the property.** When the PT pin is connected,
   the "Preset (ms)" property is not used - even though the canvas shows
   "T=...[s]". A connected PT with no value (None) means the property.
2. **A timer in a feedback loop** (e.g. the timer's Q through a gate back
   to its own IN) presents the value from the previous scan - see [The
   scan cycle and the one-scan delay](help:concept_scan_cycle).
3. **Stop and restart of the simulation** reset the timer's state (it
   counts from the start again); **Pause** keeps it.

Circuits with timers drawn out: [Typical control
circuits](help:guide_typical_circuits).
