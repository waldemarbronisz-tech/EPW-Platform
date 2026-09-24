# Typical control circuits - ready block combinations

Eight circuits that come back in every project. Each is described with
library blocks (the link opens the block's page with its truth table,
animation and examples). Signal names are examples - in a project use
the DI/DO addresses from the Point register and the bits from the bit
register.

## 1. Drive start/stop with holding and stop priority

```
DI START ─────────────────────┐
                              ├─ S ─┐
DI STOP (NC) ── NOT ──┐       │     │ RS ── Q ── DO CONTACTOR
M.AWARIA ─────────────┼─ OR-3 ┴─ R1 ┘
M.BLOKADA ────────────┘
```

Blocks: [NOT](help:block:logic.not) (a normally-closed contact),
[OR-3](help:block:logic.or3), [RS](help:block:memory.rs) (reset dominates:
STOP wins over START). The holding comes from the latch's memory - a
short START pulse is enough.

## 2. An apparatus permission (a hard interlock on the controller)

```
DI Q1 CLOSED ─────┐
M.BRAK_AWARII ────┼─ AND-3 ── Bit output (internal) M.KMG1_ZEZW
M.TRYB_AUTO ──────┘
```

The result goes to an **OUT** bit: [AND-3](help:block:logic.and3) -> "Bit
output (internal)". In Studio's apparatus register name `M.KMG1_ZEZW` as
the **Permission** of apparatus KMG1: the controller refuses CLOSE with
the reason "no permission M.KMG1_ZEZW (the bit's description)" and always
lets OPEN through. A DO point without an apparatus has its own
Permission field in the Point register.

## 3. Supervising a command

```
M.POLECENIE_ZAL ─────────┐
                         ├─ AND ── TON 2000 ms ── Q ── SR S1 ── Q ── M.ALARM_BRAK_POTW
DI POTW_ZAL ──── NOT ────┘                              ▲
M.KASUJ (IN bit from the panel) ───────────────────── R
```

The [TON](help:block:timer.ton) gives the apparatus time to switch; when
the feedback does not come, the [SR](help:block:memory.sr) remembers the
alarm until cleared from the panel (an IN bit, the write is audited).

## 4. Mismatch of two auxiliary contacts

```
DI CONTACT_CLOSED ──┐
                    ├─ XOR ── NOT ── TON 1000 ms ── M.NIEZGODNOSC
DI CONTACT_OPEN ────┘
```

[XOR](help:block:logic.xor) = FALSE when both contacts say the same (both
active or neither); [NOT](help:block:logic.not) turns that into TRUE and
the [TON](help:block:timer.ton) skips the contacts' travel time.

## 5. Fan run-on

```
DO HEATER (state) ── TOF 60000 ms ── DO FAN
```

[TOF](help:block:timer.tof): the fan runs with the heater and for a
minute after it.

## 6. A coil pulse and a restart lock-out

```
DI BUTTON ── R_TRIG ── TP 200 ms ── DO CLOSE_COIL
                        └─ Q ── NOT ── (condition of the next pulse's permission)
```

[R_TRIG](help:block:edge.rtrig) turns a held button into one event,
[TP](help:block:timer.tp) gives the coil exactly 200 ms.

## 7. A flashing indication

```
GENERATOR 1 Hz ──┐
                 ├─ AND ── DO LAMP
M.ALARM ─────────┘
```

The system generator block gives a square wave; [AND](help:block:logic.and)
with the alarm bit flashes only in alarm. A steady lamp = the alarm bit
directly.

## 8. Counting operations until service

```
DI FEEDBACK_CLOSED ── R_TRIG ── CU ┐
                                   ├─ CTU (PV=10000) ── Q ── M.PRZEGLAD
M.KASUJ_LICZNIK (IN bit) ────── R ┘
```

The [CTU](help:block:counter.ctu) counts closings, Q requests a service,
cleared from the panel after it. On CV across a restart - see
[Counters](help:concept_counters).

## Checking a circuit before it goes to site

1. [Compile](help:guide_compile_export) - zero errors, read the warnings
   about unconnected inputs.
2. [Run the simulation](help:guide_simulation) and toggle the inputs in
   the simulation panel - wires and ports show the live state, exactly as
   in the animations of the Block catalog.
3. Check the edge cases: both buttons at once, a condition dropping
   during a timer's count, a restart (latches and counters start at
   FALSE/0).
