### Jak działa

- Każde **zbocze narastające** CU zwiększa CV o 1 (trzymany CU nie liczy
  dalej).
- R = TRUE zeruje CV i ma pierwszeństwo przed CU.
- Q = TRUE, gdy CV ≥ PV (pin PV, a gdy niepodłączony — właściwość
  „Preset”). Licznik liczy dalej ponad PV.
- CV jest widoczne na kanwie w symulacji („CV=…”).

Pełny opis: [Liczniki CTU, CTD, CTUD](help:concept_counters).

### 1. Liczba załączeń do przeglądu

Zlicz załączenia stycznika; po 10 000 zgłoś przegląd: CU ←
[R_TRIG](help:block:edge.rtrig)(`Potwierdzenie`), PV = 10000, Q →
`M.PRZEGLAD`, R ← bit WE `M.KASUJ_LICZNIK` z panelu (po przeglądzie).
Uwaga: CV nie jest pamiętane po restarcie sterownika — dla trwałego
licznika wpisuj CV do rejestru retentywnego (MWR.) albo użyj liczników
łączeń panelu.

### 2. Limit prób

Po trzech nieudanych próbach rozruchu zablokuj automat: CU ←
F_TRIG(`Próba rozruchu`), PV = 3, Q → `M.BLOKADA_AUTOMATU`, R ← udany
rozruch OR kasowanie.

### 3. Dozowanie porcjami

Każdy impuls z czujnika to jedna porcja; po PV porcjach zamknij zawór i
wyzeruj: Q → zamknięcie zaworu i (przez [TP](help:block:timer.tp)) → R.
