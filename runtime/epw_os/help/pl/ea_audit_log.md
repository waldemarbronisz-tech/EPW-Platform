# Dziennik audytowy i czym różni się od rejestru zdarzeń

Strona **Audit Log** wymaga poziomu **Engineer** — zarówno żeby na nią
wejść, jak i żeby zobaczyć jej zawartość.

## Czym się różni od rejestru zdarzeń (Events)

| | Rejestr zdarzeń (Events) | Dziennik audytowy (Audit Log) |
|---|---|---|
| Zawartość | zdarzenia operacyjne: sterowania, alarmy, zmiany nastaw | zdarzenia bezpieczeństwa/konfiguracji: logowania, zmiany PIN-ów, zmiany właściwości projektu, odmowy dostępu, wejścia/wyjścia z trybu kiosku |
| Trwałość | wyłącznie w pamięci, znika po zamknięciu programu | zapisywany do bazy danych, trwały |
| Dostęp do podglądu | każdy poziom | wyłącznie Engineer |

Każdy wpis ma znacznik czasu, typ zdarzenia, kto go wywołał, opis oraz
wynik (OK/FAILED) — np. nieudaną próbę zalogowania widać tu jako
FAILED, nawet jeśli w rejestrze zdarzeń w ogóle się nie pojawi.

Dziennik audytowy zapisuje między innymi: próby logowania, zmiany
PIN-ów, zmiany języka, zmiany właściwości projektu, wejścia i wyjścia z
trybu kiosku oraz każdą odmowę dostępu ("Brak uprawnień").
