# Licznik przełączeń (trwałość mechaniczna aparatu)

Aparaty łączeniowe (wyłączniki, styczniki) mają określoną trwałość
mechaniczną — producent podaje, ile cykli łączeniowych aparat wytrzyma,
zanim będzie wymagał przeglądu lub wymiany. Program liczy to
automatycznie, na podstawie zmian stanu wejścia cyfrowego — nic
dodatkowego nie trzeba podłączać ani mierzyć.

## Co jest liczone

Dla każdego wejścia cyfrowego (DI), osobno:

- **Zamknięcia** — liczba przejść ze stanu OFF do ON,
- **Otwarcia** — liczba przejść ze stanu ON do OFF,
- **Sumaryczny czas w stanie zamkniętym** — łączny czas, jaki wejście
  spędziło w stanie ON, liczony od pierwszego uruchomienia (albo od
  ostatniego zerowania licznika),
- **Data i czas pierwszego oraz ostatniego zarejestrowanego
  przełączenia**.

Pierwszy odczyt stanu po uruchomieniu programu nie jest liczony jako
przełączenie — dopiero kolejna, rzeczywista zmiana stanu.

## Gdzie to widać

- **Digital Inputs** — kolumny Zamknięcia, Otwarcia i Czas zamknięty,
  jedna para wierszy na każde z 64 wejść.
- **Main View** — okno aparatu (kliknięcie wyłącznika/stycznika na
  schemacie) pokazuje skrót licznika; przycisk **Properties** w tym
  oknie pokazuje pełny szczegół, łącznie z datą pierwszego i ostatniego
  przełączenia.

## Trwałość danych

Liczniki są zapisywane do pliku projektu i przeżywają restart programu —
nie trzeba ich niczym uruchamiać ponownie. Zapis na dysk nie odbywa się
przy każdej zmianie stanu (to spowalniałoby przetwarzanie) — program
buforuje liczniki w pamięci i zapisuje je okresowo oraz zawsze przy
zamykaniu programu.

## Zerowanie licznika

Po fizycznej wymianie aparatu licznik należy wyzerować, żeby śledzić
trwałość NOWEGO urządzenia od zera. Zerowanie:

1. Kliknij prawym przyciskiem myszy na kolumnie Zamknięcia, Otwarcia lub
   Czas zamknięty w tabeli Digital Inputs.
2. Wybierz **Zeruj licznik przełączeń...**.
3. Potwierdź — operacji nie można cofnąć.

Wymaga poziomu **Engineer** i działa w każdym trybie pracy (nie tylko w
symulacji — to narzędzie serwisowe, używane na prawdziwym sprzęcie).
Każde zerowanie zapisuje się w [dzienniku audytowym](help://ea_audit_log),
nie tylko w rejestrze zdarzeń.

## Próg ostrzegawczy (opcjonalny)

Dla każdego wejścia można ustawić własny próg — liczbę zamknięć, po
przekroczeniu której program pokazuje ostrzeżenie (kolumna Zamknięcia w
tabeli zmienia kolor, a w oknie aparatu na Main View pojawia się
dodatkowy komunikat). Domyślnie żaden próg nie jest ustawiony — funkcja
jest w pełni opcjonalna, per aparat.

Ustawienie progu: to samo menu podręczne co zerowanie —
**Ustaw próg ostrzegawczy...** (również wymaga poziomu Engineer).
