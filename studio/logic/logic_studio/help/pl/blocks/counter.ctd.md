### Jak działa

- LD = TRUE ładuje CV wartością PV (pin albo właściwość „Preset”) i ma
  pierwszeństwo przed CD.
- Każde **zbocze narastające** CD zmniejsza CV o 1.
- Q = TRUE, gdy CV ≤ 0. Licznik liczy dalej poniżej zera.

Pełny opis: [Liczniki CTU, CTD, CTUD](help:concept_counters).

### 1. Pozostałe cykle do wymiany

Załaduj 500 (LD przy montażu nowego elementu), odejmuj po każdym cyklu;
Q → „wymień element”. CV pokazuje, ile zostało.

### 2. Odliczanie porcji

Załaduj liczbę porcji do wydania, każdy impuls dozownika odejmuje jedną;
przy zerze zamknij zawór.
