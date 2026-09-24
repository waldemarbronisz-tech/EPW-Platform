### Tabela prawdy

| In1 | In2 | Out |
|---|---|---|
| 0 | 0 | **1** |
| 1 | 0 | **1** |
| 0 | 1 | **1** |
| 1 | 1 | 0 |

NAND to [AND](help:block:logic.and) z zanegowanym wyjściem. Wejścia niepodłączone liczą się jako FALSE. Wejście **zaślepione** (zaślepka, patrz [Zaślepka wejścia](help:concept_stubs)) jest pomijane, bramka liczy wynik z pozostałych. Ogólny opis rodziny: [Bramki logiczne](help:concept_gates).

### 1. Blokada „nie oba naraz”

Dwa napędy nie mogą pracować jednocześnie (np. pompa i mieszadło z jednego
zasilacza): `Pompa pracuje` NAND `Mieszadło pracuje` → zezwolenie na
załączenie kolejnego. Dopóki pracuje najwyżej jeden, NAND daje TRUE.

### 2. Zamiennik dla NOT + AND

Gdy potrzebujesz „warunek A i B → **wyłącz**”, NAND oszczędza jeden blok:
wynik podaj bezpośrednio na wyjście, które ma być aktywne w stanie
spoczynku (np. `M.ZEZW_PODTRZYMANIE`).
