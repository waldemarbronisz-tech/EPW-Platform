### Jak działa (impuls o stałej długości)

```
IN  ____|‾‾|______|‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾|______
Q   ____|‾‾‾‾‾‾‾|_|‾‾‾‾‾‾‾|_______________
        |<-PT->|  |<-PT->|
```

- Zbocze narastające IN uruchamia impuls Q o długości **dokładnie** PT,
  niezależnie od tego, jak długo IN trwa — krócej czy dłużej.
- W czasie trwania impulsu kolejne zbocza IN są **ignorowane** (impuls
  nie jest przedłużany ani restartowany).
- ET liczy czas od początku impulsu.

Pełny opis rodziny: [Timery TON, TOF, TP](help:concept_timers).

### 1. Impuls na cewkę

Przekaźnik bistabilny albo stycznik z cewką impulsową potrzebuje impulsu
o określonej długości: `Polecenie` → TP 200 ms → `DO cewka ZAŁĄCZ`.
Operator może trzymać przycisk dowolnie długo — cewka dostanie 200 ms.

### 2. Sygnał dźwiękowy na zdarzenie

Krótki dźwięk przy każdym nowym alarmie: `Nowy alarm` → TP 1500 ms →
`DO buczek`.

### 3. Ochrona przed zbyt częstym startem

TP 30 s uruchamiany z polecenia startu, a jego Q (negowane) jako warunek
zezwolenia na kolejny start: drugi start wcześniej niż po 30 s zostanie
odrzucony.
