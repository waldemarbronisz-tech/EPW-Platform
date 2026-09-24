### Jak działa

Out jest TRUE przez **jeden skan** przy każdej zmianie In — zarówno
0→1, jak i 1→0. To [R_TRIG](help:block:edge.rtrig) OR
[F_TRIG](help:block:edge.ftrig) w jednym bloku. Pełny opis:
[Przerzutniki i detekcja zboczy](help:concept_memory_edges).

### 1. Rejestrowanie każdej zmiany położenia

Każda zmiana stanu aparatu ma zwiększyć licznik przełączeń:
CHANGE(`Potwierdzenie ZAMKNIĘTY`) → CU licznika [CTU](help:block:counter.ctu).

### 2. Wyzwolenie komunikatu

Przy każdej zmianie trybu pokaż komunikat na panelu: CHANGE(`M.AUTO`) →
blok komunikatu systemowego.

### 3. Detekcja drgań

Zbyt wiele zmian w krótkim czasie oznacza drgający styk: CHANGE →
[CTU](help:block:counter.ctu) kasowany co 10 s przez [TON](help:block:timer.ton);
Q licznika przy PV = 5 → „sprawdź styk”.
