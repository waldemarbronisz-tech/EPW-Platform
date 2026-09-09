# Historia zdarzeń alarmowych

Pełny, chronologiczny zapis wszystkiego, co zrobił system alarmowy —
na własnej stronie, Historia zdarzeń, osobno zarówno od Rejestru
zdarzeń (wszystkie zdarzenia procesowe/alarmowe w całym programie), jak
i od Dziennika audytowego (wszystkie działania bezpieczeństwa/
konfiguracji w całym programie, nie tylko tego modułu).

**Co jest zapisywane**: uzbrojenie i rozbrojenie (kto, kiedy, która
strefa), każde naruszenie linii (która linia, w jakim stanie była
strefa), każdy alarm — z oznaczeniem
[pierwszej przyczyny](help://intr_alarm_memory) — każda awaria linii i
zasilania, bypass linii i jego zdjęcie, linia oznaczona jako
Podejrzana, włączenie i wyłączenie trybu chodzenia oraz skasowanie
pamięci alarmu.

**Filtrowanie**: po strefie, po typie zdarzenia i po zakresie dat, z
paska narzędzi nad tabelą — wybierz, czego szukasz, i naciśnij
*Zastosuj filtry*. Filtrowanie wymaga tu osobnego przycisku (inaczej niż
w tabelach stref/linii powyżej, które odświeżają się same) — bo
odpytywanie bazy przy każdym pojedynczym zdarzeniu, w chwili gdy się
wydarza, byłoby zmarnowaną pracą dla widoku, który większość osób
otwiera, żeby spojrzeć wstecz, a nie oglądać na żywo.

**Eksport**: *Eksportuj CSV* zapisuje dokładnie to, co aktualnie jest na
ekranie — najpierw zastosuj filtry, potem eksportuj, tak samo jak
eksport CSV na każdej innej stronie tego programu.

**Retencja** (poziom Engineer, *Konfiguruj retencję*): maksymalna liczba
zdarzeń, maksymalny wiek w dniach, albo oba naraz — pozostawienie
któregoś na 0 oznacza brak limitu dla tej wielkości. Najstarsze
zdarzenia są usuwane automatycznie, gdy limit zostanie przekroczony,
więc ta historia nie może rosnąć w nieskończoność na urządzeniu o
ograniczonej pamięci (np. karcie SD w Orange Pi).
