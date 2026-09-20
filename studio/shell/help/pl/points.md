# Rejestr punktów

Wszystkie kanały wszystkich kart, w jednej tabeli. Punktów **nie dodaje
się tutaj** — rodzą się z [kart](help://io_cards). Tutaj im się nadaje
znaczenie.

Filtr **Karta** u góry zawęża widok do jednego modułu.

## Kolumny wspólne

| Kolumna | Co wpisać |
|---|---|
| **Adres** | `id.RODZAJ.numer` — tylko do odczytu, pochodzi z karty |
| **Opis** | co jest podłączone do tego zacisku; to czyta operator |
| **Lokalizacja** | pusta = dziedziczona z karty; można nadpisać |
| **Notatka techniczna** | dla serwisanta: numer żyły, listwa, typ czujki |
| **Aparat** | tylko do odczytu: który aparat zajął ten punkt |

**Ustaw lokalizację dla zaznaczonych…** nadaje lokalizację wielu punktom
naraz.

## Kolumny punktów analogowych (AI/AO)

| Kolumna | Znaczenie |
|---|---|
| **Typ sygnału** | `4-20mA`, `0-10V`, `0-3.3V ADC (raw)` albo „wartość gotowa" (bez przeliczania) |
| **Surowe min / max** | zakres wartości z karty |
| **Inż. min / max** | na co się to przelicza |
| **Jednostka** | `°C`, `bar`, `A`, `%` |
| **Miejsca dz.** | ile cyfr po przecinku pokazywać |

Przeliczenie jest liniowe. „Wartość gotowa" znaczy, że karta podaje już
wielkość inżynierską i nic nie trzeba skalować.

## Kolumna punktów DI

**Ostrzeżenie licznika przy** — po ilu łączeniach aparat na tym punkcie
ma się zgłosić do przeglądu. Liczy je moduł Liczników łączeń; stan
liczników podejrzysz w [Połączeniu ze
sterownikiem](help://controller).

## Tryb „Na żywo" i wymuszenia

Gdy Studio jest połączone ze sterownikiem, kolumna **Na żywo** pokazuje
bieżącą wartość każdego punktu. To samo działa w Kartach („Odpowiada")
i w edytorze ekranów.

**Tryb wymuszania (Engineer)** włącza operowanie wartością:

- **Wymuś wartość…** — przypina wybrany punkt do podanej wartości;
- **Zdejmij wymuszenie** / **Zdejmij wszystkie wymuszenia**;
- wymuszony punkt pokazuje `F → wartość` i kto go wymusił.

Wymuszenie jest narzędziem serwisanta: wymaga tokenu Engineer, jest
zapisywane w dzienniku sterownika, **utrzymuje się tylko dopóki Studio
potwierdza obecność** (heartbeat) i jest zdejmowane przy zamknięciu
połączenia, przy restarcie sterownika i przy [przeładowaniu
projektu](help://controller) — wymuszenie przypina tag, którego nowy
projekt może w ogóle nie mieć.
