### Jak działa

Out jest TRUE przez **jeden skan** — ten, w którym In zmieniło się z TRUE
na FALSE. Pełny opis: [Przerzutniki i detekcja
zboczy](help:concept_memory_edges).

### 1. Zdarzenie „zakończono”

Koniec pracy pompy (moment wyłączenia) ma uruchomić płukanie filtra:
F_TRIG(`Pompa pracuje`) → S przerzutnika sekwencji płukania.

### 2. Liczenie cykli po zakończeniu

Cykl liczy się jako wykonany dopiero po jego zakończeniu:
F_TRIG(`Cykl trwa`) → CU licznika [CTU](help:block:counter.ctu).

### 3. Wykrycie zwolnienia przycisku

Działanie ma nastąpić po puszczeniu przycisku (np. potwierdzenie
„zwolnij, by wykonać”): F_TRIG(`DI przycisk`) → [TP](help:block:timer.tp).
