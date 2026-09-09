# Wczytywanie ekranu synoptycznego (.epwsyn)

**Projekt → Wczytaj ekran synoptyczny...** (tylko **Engineer**) wczytuje
ekran schematyczny wyeksportowany z EPW Synoptic Editor (plik
`.epwsyn`) i pokazuje podsumowanie jego zawartości. Ekran **nie jest
rysowany** — to jest sprawdzenie danych, nie podgląd wizualny;
narysowanie ekranu w Widoku głównym to osobny, późniejszy krok.

Po wybraniu pliku podsumowanie pokazuje:

- nazwę projektu zapisaną w pliku,
- liczbę obiektów rysunku,
- liczbę **aparatów** w rejestrze aparatów pliku, w podziale na pięć
  zachowań — **SWITCHED** (sterowalny dwustanowy, np. stycznik lub
  zawór), **SIGNAL** (tylko sygnalizacyjny, np. lampka lub czujka),
  **MEASURED** (pomiar analogowy), **MODULATED** (sterowalny płynnie,
  np. falownik), **SELECTOR** (fizyczny przełącznik wielopozycyjny),
- ewentualne ostrzeżenia.

**Dlaczego aparaty liczą się osobno od obiektów:** w formacie Synoptic
Editora pełna konfiguracja aparatu — jego styk sprzężenia zwrotnego,
wyjście komendy, zachowanie w stanie bezpiecznym — nigdy nie jest
zapisywana na samym rysunku. Obiekt na ekranie mówi tylko "w tym
miejscu pokaż ten symbol, reprezentujący aparat X". Rzeczywista
konfiguracja aparatu znajduje się raz, w rejestrze aparatów pliku,
niezależnie od tego, na ilu obiektach (albo ekranach) się pojawia. To,
że ten sam aparat występuje na wielu obiektach, jest normalne, nie jest
błędem.

**O ostrzeżeniach:** jedyne ostrzeżenie, jakie może wygenerować to
sprawdzenie, to obiekt rysunku wskazujący na identyfikator aparatu,
którego nie ma w rejestrze pliku. Taki obiekt i tak się wczytuje —
po prostu nie ma nic do powiązania — dlatego jest to pokazane jako
ostrzeżenie, a nie powód do odrzucenia pliku. Plik jest odrzucany
tylko przy problemie strukturalnym: to nie jest plik `EPW_SYNOPTIC`,
wersja schematu jest nowsza niż obsługiwana przez tę wersję EPW OS,
brakuje wymaganego pola, albo dwa obiekty rysunku mają ten sam
identyfikator. Odrzucenie pliku z któregokolwiek z tych powodów niczego
nie zmienia — aktywny projekt pozostaje nietknięty.

Każde wczytanie (udane lub odrzucone) jest zapisywane w
[Dzienniku audytowym](help://ea_audit_log): kto, kiedy, jaki plik oraz
— przy udanym wczytaniu — ile obiektów i aparatów zawierał.
