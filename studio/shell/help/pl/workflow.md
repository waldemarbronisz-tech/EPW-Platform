# Jak powstaje projekt, krok po kroku

Kolejność nie jest dowolna: każdy krok korzysta z tego, co powstało
w poprzednim. **Karty rodzą punkty**, punkty są adresami dla aparatów,
linii dozorowych, zabezpieczeń, ekranów i logiki. Jeśli zaczniesz od
rysowania ekranu, nie będzie do czego przypiąć symboli.

Kroki 1–4 potrafi za Ciebie przeprowadzić [Kreator
urządzenia](help://wizard) (Plik → Kreator urządzenia). Reszta to
normalna praca w drzewie.

---

## Krok 1. Nowy projekt i jego informacje

Górny pasek → **Nowy**, potem dział [Informacje o
projekcie](help://info): nazwa (to ją sterownik podaje jako swój
projekt), autor, opis.

Nazwa korzenia drzewa to ta sama nazwa — dwuklik zmienia ją w miejscu.

## Krok 2. Skład urządzenia

[Skład urządzenia](help://devices) — zaznaczasz, jakie moduły ten
sterownik **ma**. Moduł spoza składu nie istnieje: jego gałąź w drzewie
się nie pokazuje, a w sterowniku nie powstaje ani obiekt, ani wątek, ani
tagi.

Zrób to przed konfiguracją, żeby nie wypełniać działów, których i tak
nie będzie.

## Krok 3. Lokalizacje

[Lokalizacje](help://locations) — krótkie kody miejsc (szafa, kotłownia,
brama). Karta stoi w jednej lokalizacji, a każdy jej punkt dziedziczy ją
domyślnie. Bez tego później nie da się odpowiedzieć na pytanie „gdzie
jest ten zacisk".

## Krok 4. Karty wejść/wyjść i magistrala

[Karty wejść/wyjść](help://io_cards) — jeden wiersz na jeden fizyczny
moduł: id (pierwszy człon każdego adresu), model, jakie ma rodzaje
kanałów i po ile, adres Modbus, lokalizacja.

**To jest moment, w którym powstają punkty.** Karta `ELA1` z 32 kanałami
DI tworzy `ELA1.DI.1` … `ELA1.DI.32` w rejestrze punktów, automatycznie.

Tu też ustawiasz samą magistralę (RTU albo TCP, port, prędkość,
parzystość).

## Krok 5. Opis punktów

[Rejestr punktów](help://points) — każdemu kanałowi piszesz, **co jest
do niego podłączone**, notatkę techniczną i ewentualnie inną lokalizację
niż dziedziczona po karcie. Dla punktów analogowych: typ sygnału,
przeliczenie surowej wartości na wielkość inżynierską, jednostkę
i liczbę miejsc po przecinku.

Ten opis jedzie na sterownik i widzi go operator przy szafie. Adres bez
opisu to numer kanału i nic więcej.

## Krok 6. Aparaty

[Rejestr aparatów](help://apparatus) — wyłącznik, stycznik, zawór:
zachowanie, punkty potwierdzenia i punkty sterujące, styl komendy
(MAINTAINED / PULSE / PULSE_TOGGLE).

Aparat jest tym, co operator naciska na ekranie i co pojawia się
w logice jako jedna rzecz, a nie jako dwa surowe wyjścia.

## Krok 7. Ekran synoptyczny

[Schemat synoptyczny](help://screens) — rysujesz obiekt i wiążesz
symbole z aparatami i punktami. Ekran jest zapisany **w projekcie**,
więc sterownik rysuje dokładnie to, co narysowałeś, bez osobnego pliku.

Tu też umieszczasz wizualizację pomiarów — wskaźniki, zbiorniki,
wartości liczbowe związane z realnymi punktami.

## Krok 8. Logika

[Logika](help://logic) — schemat blokowy na tych samych adresach.
Wejścia, bramki, przerzutniki, czasy, bloki analogowe, sygnały systemowe
`SYS.*` i alarmówki `SEC.*/REQ.SEC.*`, wyjścia.

Tu zamykasz wszystko, czego sterownik nie robi sam z siebie: np. sygnał
`SEC.SYSTEM.SIREN_ACTIVE` na wyjście, do którego fizycznie wisi syrena.

## Krok 9. Alarmówka (jeśli jest w składzie)

Po kolei: [Strefy](help://zones) → [Linie dozorowe](help://lines) →
[Użytkownicy](help://intrusion_users). Linia potrzebuje strefy, a
użytkownik potrzebuje stref, którymi ma prawo operować.

W Strefach są też nadzór zasilania i nastawy sygnalizatora.

## Krok 10. Zabezpieczenia (jeśli są w składzie)

[Zabezpieczenia elektryczne](help://protection_electrical) — nastawy
funkcji ANSI wykonywane przez kartę ADA01.
[Zabezpieczenia procesowe](help://protection_process) — progi górny
i dolny na punktach analogowych, oceniane w sterowniku.

## Krok 11. Sprawdź i zapisz

[Sprawdź projekt](help://validation) znajduje rozjazdy, których nie
widać w tabelach: aparat wskazujący nieistniejący punkt, punkt przypisany
do dwóch aparatów naraz, linię bez punktu, moduł z danymi poza składem.

Potem **Zapisz**. Dopiero zapisany plik da się wysłać — sterownik
dostaje plik z dysku, nie zawartość okna.

## Krok 12. Wyślij na sterownik

[Połączenie ze sterownikiem](help://controller) — adres, token Engineer,
**Wyślij na urządzenie**. Studio najpierw porównuje rewizje i nastawy:
jeśli ktoś zmienił coś na panelu, zobaczysz tabelę różnic, zanim
cokolwiek nadpiszesz.

Sterownik **przebudowuje się według nowego projektu bez restartu** —
karty, punkty, aparaty, komendy, alarmówka, logika i panel. Na tej samej
stronie sprawdzisz potem [stan logiki](help://controller), nastawy na
żywo i liczniki.

---

## Co jeszcze warto zrobić

- [Integracja MQTT](help://mqtt) — jeśli sterownik ma rozmawiać z Home
  Assistantem.
- [Powiązania obiektu](help://object_links) — jeśli sterowniki mają
  widzieć nawzajem swoje wartości.
- [Test zabezpieczeń](help://protection_tests) — po uruchomieniu, jako
  dowód, że zabezpieczenie zadziałało w zmierzonym czasie.
