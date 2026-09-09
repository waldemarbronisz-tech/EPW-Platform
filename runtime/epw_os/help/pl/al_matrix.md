# Co wolno na każdym poziomie — pełna tabela uprawnień

Tabela poniżej opisuje wyłącznie to, co faktycznie sprawdza kod — każda
z tych blokad jest wykonywana DWA razy: raz wizualnie (przycisk wyłączony
albo komórka nieedytowalna) i raz w momencie faktycznego wykonania
akcji, niezależnie od tego, co pokazywał interfejs chwilę wcześniej.
Dzięki temu obniżenie poziomu w trakcie (np. przez automatyczne
wylogowanie — patrz [Automatyczne wylogowanie](help://al_timeout))
zawsze zatrzyma akcję, nawet jeśli przycisk był już kiedyś aktywny.

| Czynność | Wymagany poziom |
|---|---|
| Podgląd wszystkich stron (poza Audit Log i Engineer Mode) | User |
| Sterowanie aparatem z Main View (Main View → schemat) | Operator |
| Kwitowanie alarmu (Alarmy) | Operator |
| Edycja opisu wejścia cyfrowego (Digital Inputs) | Engineer |
| Wymuszanie stanu wejścia cyfrowego w trybie symulacji (Digital Inputs) | Engineer |
| Edycja opisu wyjścia cyfrowego (Control Outputs) | Engineer |
| Edycja opisu / jednostki / notatki punktu analogowego (Analog Inputs) | Engineer |
| Dodanie / usunięcie punktu analogowego (Analog Inputs) | Engineer |
| Pełna konfiguracja punktu analogowego — przycisk Configure (Analog Inputs) | Engineer |
| Zmiana nastaw zabezpieczeń — włączanie stopnia, nastawa, histereza, zwłoka, akcja (Protection Settings) | Engineer |
| Reset statystyk zabezpieczeń (Protection Settings) | Engineer |
| Edycja właściwości projektu (Projekt → Właściwości projektu) | Engineer |
| Wejście do trybu kiosku i wyjście z niego (Ustawienia → Tryb kiosku) | Engineer |
| Podgląd strony Audit Log (nawigacja i treść) | Engineer |
| Podgląd strony Engineer Mode (weryfikacja zabezpieczeń) | Engineer |

## Czego NIE wymaga podniesienia poziomu

- Podgląd Main View, Digital Inputs, Control Outputs, Analog Inputs,
  Protection Settings, Power Quality, System Topology, Alarm, Events —
  dostępne dla każdego, w tym dla User.
- Ustawienia → Język i Wygaszanie ekranu — dostępne dla każdego poziomu.
- Eksport danych z Historiana i eksport zdarzeń do CSV — dostępne dla
  każdego poziomu.
- Pomoc (to okno) — dostępna dla każdego poziomu, bez PIN-u, także w
  trybie kiosku.

Gdy poziom jest za niski, program pokazuje komunikat "Brak uprawnień" i
zapisuje próbę w dzienniku audytowym — **nigdy** nie pyta w tym momencie
o PIN. Żeby podnieść poziom, trzeba zrobić to świadomie z górnego paska
— patrz [Zmiana poziomu i wprowadzanie PIN-u](help://al_pin).
