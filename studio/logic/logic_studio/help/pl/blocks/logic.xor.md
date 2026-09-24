### Tabela prawdy

| In1 | In2 | Out |
|---|---|---|
| 0 | 0 | 0 |
| 1 | 0 | **1** |
| 0 | 1 | **1** |
| 1 | 1 | 0 |

XOR jest TRUE, gdy wejścia są **różne** (formalnie: gdy nieparzysta liczba
wejść jest aktywna). Wejścia niepodłączone liczą się jako FALSE. Wejście **zaślepione** (zaślepka, patrz [Zaślepka wejścia](help:concept_stubs)) jest pomijane, bramka liczy wynik z pozostałych. Ogólny opis rodziny: [Bramki logiczne](help:concept_gates).

### 1. Wykrycie niezgodności potwierdzeń

Aparat ma dwa styki pomocnicze: „zamknięty” i „otwarty”. Prawidłowo
dokładnie jeden z nich jest aktywny. `Styk ZAMKNIĘTY` XOR `Styk OTWARTY`
= FALSE oznacza rozbieżność (oba albo żaden) → alarm „niezgodność
położenia”. Dodaj [TON](help:block:timer.ton), żeby nie alarmować w czasie
ruchu styków.

### 2. Schodowy dwa przyciski

Sterowanie oświetleniem z dwóch miejsc bez przerzutnika: każdy przełącznik
zmienia stan — `Przełącznik A` XOR `Przełącznik B` → światło.

### 3. Porównanie dwóch bitów

Dwa niezależne tory obliczające to samo (redundancja): XOR ich wyników =
TRUE → różnią się → sygnał do sprawdzenia.
