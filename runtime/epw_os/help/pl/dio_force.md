# Wymuszanie stanu wyjścia (Force) i dlaczego wymaga Engineera

W programie są DWIE różne funkcje wymuszania — celowo różne, dla
różnych celów.

## Force w Control Outputs

Przy każdym sterowalnym wyjściu znajduje się przycisk **Force**. Kliknięcie
otwiera potwierdzenie, a po zatwierdzeniu komenda przechodzi przez
**dokładnie ten sam mechanizm**, co zwykłe sterowanie z Main View
(łącznie z kontrolą bezpieczeństwa) — różnica jest tylko taka, że nie
trzeba w tym celu wchodzić na schemat synoptyczny. Działa zarówno w
trybie symulacji, jak i live. To narzędzie serwisowe/rozruchowe,
dlatego wymaga poziomu Engineer, podczas gdy zwykłe sterowanie z Main
View wystarczy wykonać jako Operator.

## Wymuszanie w Digital Inputs (menu podręczne)

Kliknięcie prawym przyciskiem myszy na wierszu w Digital Inputs otwiera
menu z opcjami Wymuś WŁ / Wymuś WYŁ / Przełącz / Impuls. **Działa
wyłącznie w trybie symulacji** — bezpośrednio ustawia wartość tagu
wejścia, tak jakby sygnał faktycznie nadszedł z instalacji. Służy do
testowania logiki i wizualizacji bez podłączonego sprzętu. Wymaga
poziomu Engineer.

Obie funkcje są niedostępne (przyciski/menu nieaktywne albo niewidoczne)
poniżej wymaganego poziomu, a próba wykonania akcji jest dodatkowo
sprawdzana w momencie faktycznego wykonania.
