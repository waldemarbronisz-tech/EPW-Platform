# Retencja danych

**Ustawienia → Retencja danych...** (poziom Engineer) kontroluje, jak
długo przechowywane są dwa różne rodzaje historii: dane pomiarowe
Historiana oraz zapis dziennika audytowego o tym, kto co zmienił.
**Obie opcje są domyślnie WYŁĄCZONE — dopóki nie skonfigurujesz limitu,
program zachowuje się dokładnie tak jak zawsze, i nic nigdy nie jest
usuwane.**

## Dlaczego to dwa osobne ustawienia, a nie jedno

**Historian** zapisuje wartości tagów w czasie — trend tego, co robił
dany pomiar. Stare pomiary z czasem przestają być użyteczne, a na karcie
pamięci o ograniczonej pojemności (docelową platformą tego programu jest
Orange Pi, często z kartą SD) pozwolenie tej tabeli rosnąć w
nieskończoność nie jest zrównoważone.

**Dziennik audytowy** to co innego: to zapis tego, *kto co zrobił* —
logowania, zmiany PIN-u, kto i kiedy zmienił nastawę zabezpieczenia.
Ciche usuwanie starych wpisów audytowych oznaczałoby, że za rok nie da
się odpowiedzieć na pytanie "kto zmienił tę nastawę zabezpieczenia?".
To nie jest ten sam problem co pomiar, który przestał być interesujący,
więc nie dostaje tego samego rozwiązania.

## Retencja Historiana

Ustaw maksymalny wiek (w dniach) i/lub maksymalną liczbę wierszy —
jedno, oba, albo żadne (0 oznacza "bez limitu" dla danej osi). Który
limit zostanie przekroczony, taki jest usuwany — zawsze najpierw
*najstarsze* wiersze. Odbywa się to w tle, na własnym wątku roboczym
Historiana — nigdy nie blokuje zapisu tagu ani interfejsu. Za każdym
razem, gdy wiersze zostaną usunięte, zapisywana jest do dziennika
aplikacji (a jeśli dostępny — także do dziennika audytowego) informacja
ile wierszy i z jakiego zakresu dat.

## Retencja dziennika audytowego — najpierw archiwum, zawsze

Dziennikowi audytowemu również można ustawić maksymalny wiek i/lub
liczbę wierszy. Kluczowa różnica: **zanim jakikolwiek wiersz dziennika
audytowego zostanie usunięty, jest najpierw zapisywany do pliku
archiwalnego CSV — zwykłego formatu tekstowego, który otworzy dowolny
arkusz kalkulacyjny, bez potrzeby specjalnego oprogramowania.** Jeśli
ten zapis archiwum się nie powiedzie z jakiegokolwiek powodu (brak
miejsca na dysku, folder bez uprawnień do zapisu), **nic nie zostaje
usunięte** — baza danych pozostaje dokładnie taka, jaka była. Folder
archiwum jest konfigurowalny (przycisk Przeglądaj... w oknie dialogowym);
pozostawiony pusty, użyta zostanie wbudowana lokalizacja domyślna obok
bazy danych.

Gdy cykl archiwizacji i usunięcia się powiedzie, sam dziennik audytowy
otrzymuje jeden nowy wpis zapisujący, że to się wydarzyło — ile wierszy,
z jakiego zakresu dat i do którego pliku archiwum — więc sam fakt, że
stare wpisy zostały wyczyszczone, nigdy nie jest niewidoczny.

## Rozmiar bazy danych

Okno dialogowe pokazuje bieżący rozmiar pliku bazy danych i liczbę
wierszy w każdej tabeli, dzięki czemu można ocenić, czy retencja jest
w ogóle potrzebna, zanim cokolwiek się skonfiguruje. Osobny, opcjonalny
próg ostrzegawczy (w MB) pokazuje wskaźnik na pasku statusu, gdy plik
bazy danych przekroczy zadany rozmiar — niezależnie od dwóch ustawień
retencji powyżej, ponieważ dotyczy całego pliku, a nie limitu per
tabela.
