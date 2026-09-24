# Liczniki CTU, CTD, CTUD

Licznik zlicza **zbocza narastające** na swoim wejściu zliczającym —
trzymany sygnał liczy się raz. Wartość CV jest widoczna na kanwie w
symulacji („CV=…”), a Q mówi, czy osiągnięto wartość zadaną.

| Blok | Liczy | Ładowanie/kasowanie | Q |
|---|---|---|---|
| [CTU](help:block:counter.ctu) | w górę (CU) | R zeruje (ma pierwszeństwo) | CV ≥ PV |
| [CTD](help:block:counter.ctd) | w dół (CD) | LD ładuje PV (ma pierwszeństwo) | CV ≤ 0 |
| [CTUD](help:block:counter.ctud) | w górę (CU) i w dół (CD) | R zeruje > LD ładuje > CU/CD | QU: CV ≥ PV, QD: CV ≤ 0 |

PV bierze się z pinu PV, a gdy jest niepodłączony — z właściwości
„Preset”. Licznik liczy dalej ponad PV (CTU) i poniżej zera (CTD) — Q po
prostu pozostaje TRUE.

## Co warto wiedzieć

- **Zbocze, nie stan.** CTU z CU podłączonym do sygnału trwającego wiele
  skanów zliczy go raz. Jeśli zliczasz zdarzenie złożone, blok
  [R_TRIG](help:block:edge.rtrig) przed CU dokumentuje ten zamiar na
  schemacie, choć technicznie nie jest konieczny.
- **CV nie przeżywa restartu.** Po restarcie sterownika i po stopie
  symulacji licznik zaczyna od zera (CTU) lub od PV po LD. Trwały stan
  wymaga zapisu do rejestru retentywnego (MWR.) albo użycia liczników
  łączeń panelu (Rejestr punktów → liczniki).
- **Dwa zbocza w jednym skanie** (CTUD, CU i CD naraz) znoszą się.
- **Q jako warunek**: Q licznika bywa sygnałem długotrwałym (trwa, dopóki
  CV ≥ PV). Jeżeli potrzebujesz impulsu „osiągnięto”, przepuść Q przez
  [R_TRIG](help:block:edge.rtrig).

## Typowe zastosowania

- liczba załączeń do przeglądu (CTU, kasowanie z panelu),
- limit prób rozruchu (CTU + blokada automatu),
- odliczanie pozostałych cykli (CTD, LD przy wymianie części),
- bilans wejść/wyjść — osoby, pojazdy, porcje (CTUD, QU „pełno”, QD
  „pusto”).

Rozrysowane układy: [Typowe układy sterowania](help:guide_typical_circuits).
