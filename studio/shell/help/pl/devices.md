# Skład urządzenia

Z jakich **modułów** składa się ten sterownik. Nie karty — funkcje.

Zaznaczenie decyduje o dwóch rzeczach naraz:

- **w Studiu** — czy gałąź tego modułu w ogóle pojawia się w drzewie;
- **w sterowniku** — czy moduł jest tworzony. Moduł spoza składu nie ma
  obiektu, nie ma wątku, nie ma tagów. Nie jest „wyłączony" — go nie ma.

## Kolumny

**Nazwa**, **Opis**, **Aktywny** (TAK/NIE — kliknięcie przełącza).

## Moduły

| Moduł | Co wnosi |
|---|---|
| Alarmówka | strefy, linie dozorowe, uzbrajanie |
| Zabezpieczenia elektryczne | nastawy ANSI realizowane przez ADA01 |
| Zabezpieczenia procesowe | progi na punktach analogowych |
| Trendy | historia wartości (Historian) |
| Jakość zasilania | parametry sieci: napięcie, THD, asymetria |
| Diagnostyka magistrali | liczniki ramek i błędów |
| Topologia systemu | widok faktycznego składu instalacji |
| Tryb inżynierski | dodatkowe narzędzia na poziomie Engineer |
| Wejścia analogowe | czy sterownik w ogóle obsługuje punkty AI |
| Liczniki łączeń | zliczanie załączeń i czasu pracy aparatów |
| Notatki serwisowe | dziennik serwisanta przy punktach |
| Historia alarmów | dziennik zdarzeń alarmówki |
| Podgląd alarmówki | żywy podgląd stref i linii na panelu |

## Wyłączenie nigdy nie kasuje danych

Jeśli moduł ma już dane w projekcie, Studio ostrzega wprost: gałąź
zniknie z drzewa, ale **dane zostają**. Ponowne włączenie przywraca je
w całości. Tak samo w sterowniku.

Moduł z danymi, ale poza składem, zgłasza [Sprawdź
projekt](help://validation) jako ostrzeżenie — nie błąd.
