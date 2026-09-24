### Jak działa (opóźnienie wyłączenia)

```
IN  ______|‾‾‾‾‾‾‾‾‾‾‾‾|______________________________
Q   ______|‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾|__________________
                       |<-- PT --->|
```

- Q staje się TRUE **natychmiast** z IN.
- Po spadku IN na FALSE Q trzyma jeszcze przez PT ms, potem gaśnie.
- Jeśli IN wróci na TRUE w czasie odliczania, odliczanie jest porzucone —
  Q trwa dalej, a PT liczy się od kolejnego spadku (przedłużanie).
- ET liczy czas od spadku IN (w ms, maksymalnie PT).

Pełny opis rodziny: [Timery TON, TOF, TP](help:concept_timers).

### 1. Wybieg wentylatora

Wentylator ma pracować jeszcze 60 s po wyłączeniu grzałki, żeby ją
schłodzić: `Grzałka pracuje` → TOF 60000 ms → `DO wentylator`.

### 2. Światło na czujnik ruchu

`DI czujnik ruchu` → TOF 120000 ms → `DO oświetlenie`. Każdy nowy ruch
przedłuża świecenie o pełne 2 minuty.

### 3. Podtrzymanie sygnału krótkiego

Impuls z licznika trwa jeden skan — zbyt krótko dla lampki. TOF 500 ms
wydłuża go tak, by był widoczny.
