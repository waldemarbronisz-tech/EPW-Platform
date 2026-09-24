### Tabela prawdy

| In1 | In2 | Out |
|---|---|---|
| 0 | 0 | 0 |
| 1 | 0 | 0 |
| 0 | 1 | 0 |
| 1 | 1 | **1** |

Wejścia niepodłączone liczą się jako FALSE. Wejście **zaślepione** (zaślepka, patrz [Zaślepka wejścia](help:concept_stubs)) jest pomijane, bramka liczy wynik z pozostałych. Ogólny opis rodziny: [Bramki logiczne](help:concept_gates).

### 1. Zezwolenie na załączenie — wszystkie warunki naraz

Stycznik pompy wolno załączyć tylko wtedy, gdy **jest zasilanie** i **nie ma
awarii** i **wyłącznik główny jest zamknięty**. Każdy z tych warunków to
jedno wejście bramki; dla trzech warunków weź [AND-3](help:block:logic.and3).
Wynik podłącz do bloku „Wyjście bitowe (wewn.)” z bitem WY, np.
`M.PUMP_ZEZW`, i wskaż ten bit jako **Zezwolenie** aparatu w rejestrze
aparatów Studia — sterownik odrzuci polecenie ZAŁĄCZ, gdy bit jest FALSE,
z powodem nazywającym bit.

### 2. Potwierdzenie z dwóch źródeł

Sygnał „brama zamknięta” ma być prawdziwy tylko wtedy, gdy potwierdzają
to **oba** krańcówki (lewe i prawe skrzydło): `DI krańcówka L` AND
`DI krańcówka P` → lampka „ZAMKNIĘTA”.

### 3. Uzbrojenie sekwencyjne

Przycisk START działa dopiero po wciśnięciu przycisku ARM: `ARM` AND
`START` → impuls do [TP](help:block:timer.tp) lub wejście S przerzutnika
[SR](help:block:memory.sr). Chroni przed przypadkowym startem jednym
przyciskiem.
