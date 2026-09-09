# Historia serwisowa (notatki)

Uzupełnienie [licznika przełączeń](help://dio_switching_counters):
licznik mówi ILE razy aparat zadziałał, notatka mówi CO SIĘ Z NIM
DZIAŁO. Razem dają pełną historię aparatu, nie tylko jego bieżący stan.

## Czym to nie jest

Notatka serwisowa to **NIE to samo** co [dziennik audytowy](help://ea_audit_log).
Dziennik audytowy zapisuje się sam, automatycznie, przy określonych
działaniach w systemie (logowanie, zmiana ustawienia). Notatkę zawsze
wpisuje człowiek, ręcznie, kiedy uzna, że warto coś zapisać — program
nigdy nie dodaje jej sam.

## Co zawiera wpis

- Treść — dowolny tekst, wpisany przez operatora,
- data i czas wpisania,
- poziom dostępu, na jakim wpis dodano (Operator albo Engineer — User
  nie może dodawać wpisów).

## Gdzie to znaleźć

- **Digital Inputs** i **Control Outputs** — przycisk **Notatki...** w
  osobnej kolumnie, w każdym wierszu.
- **Main View** — okno aparatu (kliknięcie wyłącznika/stycznika) →
  przycisk **Properties** → zakładka **Notatki**.

Podgląd wpisów jest dostępny dla każdego poziomu, bez ograniczeń —
również dla User.

## Dodawanie wpisu

Wymaga poziomu **Operator** lub wyższego. Pole tekstowe i przycisk
dodawania są nieaktywne poniżej tego poziomu.

## Wpisów nie da się poprawić ani usunąć

To jest zamierzone — historia serwisowa jest dziennikiem, nie
notatnikiem. Żaden poziom dostępu, łącznie z Engineerem, nie ma
możliwości edycji ani usunięcia istniejącego wpisu. Pomyłkę koryguje
się przez dodanie KOLEJNEGO wpisu z poprawką — tak jak w papierowym
dzienniku eksploatacji, gdzie błędu też się nie wymazuje, tylko
dopisuje sprostowanie.

## Eksport do CSV

Przycisk **Eksportuj do CSV...** (w oknie właściwości aparatu na Main
View oraz w oknie notatek otwartym z tabeli DI/DO) zapisuje jeden plik
CSV zawierający zarówno bieżące dane aparatu (opis, liczniki
przełączeń, jeśli dostępne), jak i pełną historię notatek, od
najstarszej do najnowszej. Treść notatek w eksporcie jest identyczna
jak wpisana — nie jest tłumaczona ani w żaden sposób zmieniana.
