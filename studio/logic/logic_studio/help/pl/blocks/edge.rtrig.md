### Jak działa

Out jest TRUE przez **jeden skan** — ten, w którym In zmieniło się z
FALSE na TRUE. W kolejnym skanie Out wraca na FALSE, choć In dalej trwa.

Uwaga na start: w pierwszym skanie po uruchomieniu logiki poprzedni stan
jest FALSE, więc wejście, które od razu jest TRUE, da jeden impuls.
Pełny opis: [Przerzutniki i detekcja zboczy](help:concept_memory_edges).

### 1. Przycisk „zmień” zamiast „trzymaj”

Operator wciska przycisk raz — stan ma się przełączyć: `DI przycisk` →
R_TRIG → wejście CU licznika [CTUD](help:block:counter.ctud) albo
naprzemienne S/R przerzutnika. Bez detekcji zbocza trzymany przycisk
przełączałby stan w każdym skanie.

### 2. Zliczanie zdarzeń

Licznik [CTU](help:block:counter.ctu) sam reaguje na zbocze CU, ale gdy
zliczasz zdarzenie złożone (np. AND kilku warunków), R_TRIG przed
wejściem CU jasno pokazuje na schemacie, że chodzi o **moment** spełnienia
warunku.

### 3. Jednorazowe zapisanie wartości

W chwili startu pompy zapamiętaj poziom w zbiorniku: R_TRIG(`Pompa
pracuje`) jako sygnał „zapisz teraz”.
