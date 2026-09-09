# Uruchomienie programu

Program uruchamia się poleceniem `python main.py`. Przy starcie EPW OS:

1. Wczytuje projekt (`project.json`) — konfigurację punktów, opisów,
   metadanych projektu.
2. Uruchamia sterowniki komunikacyjne i rejestruje urządzenia.
3. Uruchamia Historian (zapis danych historycznych) i wykonuje migracje
   bazy danych, jeśli to pierwsze uruchomienie.
4. Uruchamia monitor synchronizacji czasu.
5. Uruchamia monitor stanu zdrowia systemu (patrz
   [Monitorowanie zdrowia systemu](help://saf_kernel)).
6. Otwiera główne okno na poziomie dostępu **User**.

## Uruchomienie w trybie kiosku

Dodanie parametru `--kiosk` przy starcie (`python main.py --kiosk`)
uruchamia program od razu w trybie pełnoekranowym, bez ramki okna.
Więcej o tym trybie: [Tryb kiosku](help://kiosk_what).

## Pierwsze uruchomienie — PIN-y

Przy zupełnie pierwszym uruchomieniu program losuje PIN-y dla poziomów
Operator i Engineer i pokazuje je JEDEN RAZ w dzienniku startowym
(konsoli). Zapisz je od razu — więcej w rozdziale
[Zapomniany PIN](help://ts_forgot_pin).
