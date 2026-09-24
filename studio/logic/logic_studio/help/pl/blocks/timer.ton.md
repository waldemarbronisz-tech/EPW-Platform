### Jak działa (opóźnienie załączenia)

```
IN  ‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾___________
Q   ___________|‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾___________
    |<-- PT -->|
```

- Q staje się TRUE, gdy IN jest TRUE **nieprzerwanie** przez PT ms.
- Każdy spadek IN na FALSE natychmiast zeruje Q i czas — odliczanie
  zaczyna się od nowa przy następnym zboczu IN.
- ET pokazuje upływający czas (w ms, maksymalnie PT).
- Czas: pin PT (gdy podłączony) ma pierwszeństwo przed właściwością
  „Preset (ms)”.

Pełny opis rodziny: [Timery TON, TOF, TP](help:concept_timers).

### 1. Filtr drgań styku / potwierdzenie stabilne

Krańcówka bramy drga przy domykaniu. `DI krańcówka` → TON 300 ms →
„brama zamknięta”: sygnał musi być stabilny 0,3 s, zanim logika go uzna.

### 2. Nadzór wykonania polecenia

Po poleceniu ZAŁĄCZ aparat ma 2 s na potwierdzenie: `Polecenie` AND
NOT `Potwierdzenie` → TON 2000 ms → `M.BRAK_POTWIERDZENIA` → alarm.
Gdy potwierdzenie przyjdzie na czas, wejście TON spada i alarm nie
powstaje.

### 3. Sekwencja rozruchu

Najpierw pompa obiegowa, po 5 s kocioł: `Start` → TON 5000 ms → zezwolenie
kotła. Kilka TON o rosnących czasach z jednego sygnału startu daje prostą
sekwencję czasową.
