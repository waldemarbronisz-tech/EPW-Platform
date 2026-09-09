# Układ ekranu: menu, pasek statusu, nawigacja

## Pasek menu (górny)

**Plik** — nowy/otwórz/zapisz/zapisz jako/eksport/import projektu
(patrz [Menu Plik](help://gs_file_menu)).
**Widok** — tryb pełnoekranowy (zobacz
[Tryb kiosku a tryb pełnoekranowy](help://kiosk_vs_fullscreen)).
**Projekt** — właściwości projektu i lista ostatnio otwieranych (patrz
[Menu Projekt](help://gs_project_menu)).
**Narzędzia** — eksport danych historycznych, tryb prezentacji.
**Ustawienia** — język, zmiana PIN-u, wygaszanie ekranu, klawiatura
ekranowa, motyw wizualny, konfiguracja funkcji, integracja MQTT, tryb
ćwiczebny, tryb kiosku.
**Pomoc** — to okno, indeks oraz "O programie".

W trybie kiosku pasek menu jest ukryty poniżej poziomu Engineer —
szczegóły w rozdziale [Tryb kiosku](help://kiosk_what).

## Górny pasek informacyjny

Zegar, nazwa projektu, przełącznik poziomu dostępu, licznik alarmów
oraz status komunikacji ("COMM: OK" / "COMM: N OFFLINE" — zależny od
tego, czy jakiekolwiek urządzenie ma status OFFLINE).

## Dolny pasek statusu

Po lewej: kilka pól informacyjnych, wskaźnik synchronizacji czasu (na
zielono/czerwono/oliwkowo — patrz
[Wskaźnik synchronizacji czasu na czerwono](help://ts_time_sync)) oraz
numer wersji. Po prawej: przycisk trybu pracy (SYMULACJA/LIVE),
kliknięcie przełącza tryb.

**User** — Twój aktualny poziom dostępu (User/Operator/Engineer),
kolorowany tak samo jak rozwijana lista poziomu dostępu na górnym pasku.
Aktualizuje się natychmiast przy każdej zmianie poziomu, także przy
automatycznym wylogowaniu po 5 minutach bezczynności — zawsze pokazuje
poziom faktycznie obowiązujący, nigdy stałą nazwę.

**DB** — stan bazy danych/Historiana, sprawdzany co kilka sekund (nie
przy każdej zmianie tagu): zielony **OK**, bursztynowy **WOLNA** gdy
kolejka zapisu rośnie, czerwony **BŁĄD** gdy baza lub Historian nie
działają.

**Latency** — czas obiegu ostatniej zakończonej komendy (od żądania do
potwierdzonego sprzężenia zwrotnego, timeoutu lub odrzucenia). Pokazuje
"brak danych" do czasu pierwszej komendy w tej sesji.

**Scan** — rzeczywisty, zmierzony czas trwania cyklu odpytywania
sterownika, aktualizowany po każdym cyklu. Pokazuje "brak danych" do
czasu pierwszego cyklu.

**Q: N%** (górny pasek) — procent czterech głównych urządzeń
(Orange Pi, ELA-01, ADA-01, Modbus) aktualnie zgłaszających status
ONLINE. Ten sam zestaw danych, z którego budowany jest wskaźnik
"COMM: OK" / "COMM: N OFFLINE" obok niego.

Było tu kiedyś też pole **FPS**. Zostało usunięte zamiast podłączone do
realnej wartości: program nie ma jednej, ciągłej pętli odświeżania
całego okna, z której dałoby się sensownie zmierzyć liczbę klatek na
sekundę (kilka pojedynczych stron odświeża się na własnym timerze, np.
diagram Topologii Systemu, ale to nie jest "FPS interfejsu") — liczba w
tym miejscu byłaby po prostu inaczej wyglądającą zmyśloną wartością, nie
realną.

## Panel nawigacji (lewa strona)

Drzewo, pogrupowane tematycznie: Widok główny; Sterowanie (Wejścia
cyfrowe/analogowe, Wyjścia sterujące); System alarmowy (patrz
[Czym jest system alarmowy](help://intr_what) — jego własny podział na
trzy strony); Pomiary (Jakość energii, Trendy); Zdarzenia (Rejestr
zdarzeń, Alarmy, Dziennik audytowy); Diagnostyka (Topologia systemu,
Diagnostyka magistrali, Tryb inżyniera); oraz Nastawy zabezpieczeń
(Elektryczne, Procesowe — patrz
[Zabezpieczenia elektryczne a procesowe](help://prot_what)). Kliknięcie
w nazwę grupy otwiera pierwszą stronę w niej; kliknięcie w kwadratowy
przełącznik **[+]**/**[-]** obok grupy tylko ją rozwija albo zwija.
Grupa, w której włączona zostaje tylko jedna strona, zwija się do
pojedynczej pozycji zamiast grupy do rozwinięcia — to, ile stron dana
grupa faktycznie ma (a więc czy akurat jest zwinięta), zależy od
Konfiguracji funkcji, tak samo jak reszta tego rozdziału.

To, które grupy i strony w ogóle się pojawiają, zależy od tego, które
funkcje są włączone — patrz
[Konfiguracja funkcji](help://set_feature_config). Grupa, w której
wszystkie strony są wyłączone, znika całkowicie, nie tylko jej strony.
Kolorowy kwadracik przy nazwie grupy (nawet gdy jest zwinięta) oznacza,
że coś w środku wymaga uwagi — niepotwierdzony alarm, aktywny alarm
włamaniowy, awaria linii albo niepotwierdzona pamięć alarmu.

Dostępność treści na niektórych z tych stron zależy od poziomu dostępu
— patrz [Poziomy dostępu](help://al_matrix).

## Podpowiedzi (tooltips)

Najechanie na większość przycisków, pól paska statusu i wskaźników
pokazuje krótką podpowiedź wyjaśniającą, czym dana rzecz jest lub co
robi — to bierna podpowiedź, nie osobna funkcja do włączania/wyłączania.
