### Tabela prawdy

| In1 | In2 | Out |
|---|---|---|
| 0 | 0 | **1** |
| 1 | 0 | 0 |
| 0 | 1 | 0 |
| 1 | 1 | **1** |

XNOR to [XOR](help:block:logic.xor) z zanegowanym wyjściem: TRUE, gdy
wejścia są **jednakowe**. Wejścia niepodłączone liczą się jako FALSE. Wejście **zaślepione** (zaślepka, patrz [Zaślepka wejścia](help:concept_stubs)) jest pomijane, bramka liczy wynik z pozostałych. Ogólny opis rodziny: [Bramki logiczne](help:concept_gates).

### 1. Zgodność polecenia z potwierdzeniem

`Polecenie ZAŁĄCZ` XNOR `Potwierdzenie ZAŁĄCZONY` → TRUE, gdy aparat jest
w stanie, w jakim ma być. Przez [TOF](help:block:timer.tof) lub
[TON](help:block:timer.ton) daj czas na przełączenie, zanim FALSE zgłosi
„aparat nie wykonał polecenia”.

### 2. Synchronizacja dwóch napędów

Dwie bramy mają być zawsze w tym samym położeniu: `Brama 1 otwarta` XNOR
`Brama 2 otwarta` = FALSE → niezgodność → zatrzymaj obie.
