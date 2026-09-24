### Tabela prawdy

| In1 | In2 | Out |
|---|---|---|
| 0 | 0 | **1** |
| 1 | 0 | 0 |
| 0 | 1 | 0 |
| 1 | 1 | 0 |

NOR to [OR](help:block:logic.or) z zanegowanym wyjściem — TRUE tylko wtedy,
gdy **żadne** wejście nie jest aktywne. Wejścia niepodłączone liczą się jako FALSE. Wejście **zaślepione** (zaślepka, patrz [Zaślepka wejścia](help:concept_stubs)) jest pomijane, bramka liczy wynik z pozostałych. Ogólny opis rodziny: [Bramki logiczne](help:concept_gates).

### 1. Lampka „wszystko w porządku”

`Alarm 1` NOR `Alarm 2` → lampka zielona: świeci, dopóki nie ma żadnego
alarmu; zgaśnie przy pierwszym.

### 2. Zezwolenie bez blokad

`Blokada serwisowa` NOR `Blokada od zabezpieczenia` → `M.ZEZW`: zezwolenie
jest, gdy nie działa żadna blokada. Czytelniejsze niż NOT + NOT + AND.
