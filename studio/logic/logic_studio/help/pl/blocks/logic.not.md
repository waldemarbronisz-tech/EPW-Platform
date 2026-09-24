### Tabela prawdy

| In1 | Out |
|---|---|
| 0 | **1** |
| 1 | 0 |

Wejścia niepodłączone liczą się jako FALSE. Wejście **zaślepione** (zaślepka, patrz [Zaślepka wejścia](help:concept_stubs)) jest pomijane, bramka liczy wynik z pozostałych. Ogólny opis rodziny: [Bramki logiczne](help:concept_gates).

### 1. Styk rozwierny (NC)

Przycisk STOP i wyłączniki bezpieczeństwa są zwykle stykami **rozwiernymi**:
w spoczynku dają TRUE na wejściu, po naciśnięciu FALSE. Żeby logika
liczyła „naciśnięty”, zaneguj wejście: `DI STOP (NC)` → NOT →
`M.STOP_WCISNIETY`. Zerwanie przewodu też da „naciśnięty” — to jest
celowe (bezpieczne).

### 2. Negacja warunku dla zezwolenia

Zezwolenie ma być, gdy **nie ma** alarmu: `Alarm` → NOT → wejście
[AND](help:block:logic.and) zezwolenia. Przy kilku negowanych warunkach
rozważ [NOR](help:block:logic.nor) zamiast kilku NOT.

### 3. Lampka odwrotna

Lampka „STOP” świeci, gdy napęd **nie** pracuje: `Napęd pracuje` → NOT →
`DO lampka STOP`.
