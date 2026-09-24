### Jak działa

| R1 | S | Q |
|---|---|---|
| 0 | 0 | bez zmian (pamięta) |
| 0 | 1 | **1** |
| 1 | 0 | 0 |
| 1 | 1 | 0 — Reset dominuje |

Jak [SR](help:block:memory.sr), ale gdy oba wejścia są aktywne, wygrywa
**R1**. To jest bezpieczniejszy wybór wszędzie tam, gdzie R to STOP,
awaria albo blokada: nawet trzymany przycisk START nie utrzyma napędu,
gdy trwa STOP. Pełny opis: [Przerzutniki i detekcja
zboczy](help:concept_memory_edges).

### 1. Start/stop napędu z priorytetem stopu

`START` → S, `STOP` OR `Awaria` OR `Blokada` ([OR-3](help:block:logic.or3))
→ R1, Q → `DO stycznik`. Przykład rozrysowany krok po kroku w [Typowych
układach sterowania](help:guide_typical_circuits).

### 2. Uzbrojenie z automatycznym rozbrojeniem

`Uzbrój` → S, `Sabotaż` OR `Rozbrój` → R1. Sabotaż zawsze rozbraja,
niezależnie od trzymanego przycisku uzbrojenia.
