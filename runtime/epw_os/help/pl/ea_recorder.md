# Rejestr zdarzeń

Strona **Events** to bieżący rejestr zdarzeń operacyjnych: sterowania,
alarmów, zmian nastaw, awarii. Każdy wiersz ma znacznik czasu,
priorytet, grupę, obiekt, opis zdarzenia, użytkownika, tryb pracy i
wynik.

Wiersze są kolorowane wg priorytetu: żółty (OSTRZEŻENIE), czerwony
(ALARM), fioletowy (AWARIA), ciemnoczerwony (WYŁĄCZENIE), błękitny
(zdarzenia systemowe), zielony (pozostałe).

## Filtrowanie i wyszukiwanie

Pole tekstowe nad tabelą przeszukuje wszystkie kolumny jednocześnie.
Rozwijana lista Grupa zawęża widok do jednej kategorii (PROTECTION,
OPERATION, AUTOMATION, ENVIRONMENT, SYSTEM). Kliknięcie nagłówka kolumny
sortuje po niej (kolejne kliknięcia: rosnąco, malejąco, powrót do
domyślnego sortowania po czasie).

**Ważne**: ten rejestr istnieje wyłącznie w pamięci programu — nie jest
zapisywany do bazy danych i znika przy zamknięciu programu (chyba że
wcześniej wyeksportowany). To zasadnicza różnica względem dziennika
audytowego — patrz
[Dziennik audytowy i czym różni się od rejestru zdarzeń](help://ea_audit_log).

Rejestr przechowuje też tylko **5000** najnowszych zdarzeń w ramach
jednego uruchomienia — po przekroczeniu tej liczby najstarsze wpisy po
cichu znikają w miarę pojawiania się nowych, żeby strona zostawała
responsywna przy programie działającym bardzo długo. Jeśli starsze
wpisy mają zostać zachowane, wyeksportuj je najpierw do CSV.
