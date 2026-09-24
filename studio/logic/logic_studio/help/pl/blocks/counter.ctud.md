### Jak działa

- CU zwiększa, CD zmniejsza CV (każde na własne zbocze narastające; oba
  w jednym skanie znoszą się).
- R zeruje (najwyższy priorytet), LD ładuje PV (przed CU/CD).
- QU = TRUE, gdy CV ≥ PV; QD = TRUE, gdy CV ≤ 0.

Pełny opis: [Liczniki CTU, CTD, CTUD](help:concept_counters).

### 1. Liczba osób / pojazdów w strefie

Wjazd → CU, wyjazd → CD, PV = pojemność; QU → „parking pełny”, QD →
„parking pusty”. R z panelu do ręcznej korekty.

### 2. Bilans wsadów w zbiorniku buforowym

Napełnienie porcją → CU, pobranie porcji → CD; QU blokuje kolejne
napełnienie, QD blokuje pobór.
