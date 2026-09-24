### Tabela prawdy

| In1 | In2 | Out |
|---|---|---|
| 0 | 0 | 0 |
| 1 | 0 | **1** |
| 0 | 1 | **1** |
| 1 | 1 | **1** |

Wejścia niepodłączone liczą się jako FALSE. Wejście **zaślepione** (zaślepka, patrz [Zaślepka wejścia](help:concept_stubs)) jest pomijane, bramka liczy wynik z pozostałych. Ogólny opis rodziny: [Bramki logiczne](help:concept_gates).

### 1. Alarm zbiorczy

Sygnalizator ma się odezwać, gdy zadziała **którekolwiek** zabezpieczenie:
`Przeciążenie` OR `Zwarcie doziemne` → `M.ALARM_ZBIORCZY` → syrena. Przy
większej liczbie źródeł: [OR-3](help:block:logic.or3), [OR-4](help:block:logic.or4)
albo kaskada bramek.

### 2. Sterowanie z dwóch miejsc

Oświetlenie korytarza ma załączać przycisk przy wejściu **lub** przycisk
na panelu: `DI przycisk 1` OR `Bit z panelu M.SWIATLO` → wejście S
przerzutnika [SR](help:block:memory.sr).

### 3. Warunek stopu

Pompa ma się zatrzymać, gdy `STOP z panelu` OR `Sucho­bieg` OR
`Przegrzanie`. Wynik OR na wejście R przerzutnika, który trzyma pracę
pompy — patrz [Typowe układy sterowania](help:guide_typical_circuits).
