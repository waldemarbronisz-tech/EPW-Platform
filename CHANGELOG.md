# Historia zmian

Wersje trzech programów są niezależne, ale 1.0 osiągają razem — bo
razem tworzą platformę, którą da się zainstalować u kogoś w domu i
zostawić.

---

## 1.0.0 — 2026-09-20

EPW OS 1.0.0 · EPW Studio 1.0.0 · EPW Logic Studio 1.0.0

Pierwsze wydanie, w którym **cała droga jest zamknięta**: projekt
powstaje w Studiu, jedzie na sterownik, sterownik go wykonuje, a gdy
padnie karta — wraca z kopii zapasowej.

### Sterownik wykonuje logikę

Program logiki zbudowany w Logic Studio jedzie **skompilowany w
projekcie** i pracuje na sterowniku we własnym skanie. Pasek stanu mówi,
czy naprawdę chodzi: liczba bloków, czas cyklu, najdłuższy skan, ile
wyjść prowadzi. Zatrzymanie skanu sprowadza te wyjścia do stanu
bezpiecznego. Wyjście prowadzone przez logikę jest zablokowane dla
obsługi ręcznej — dopóki skan pracuje.

Program da się przeładować bez restartu (Engineer, dziennik).

Sygnały: `SYS.*`, bity wewnętrzne i retencyjne (`MR.`/`MWR.`,
przeżywają restart) oraz pełna alarmówka przez `SEC.SYSTEM.*` i `REQ.SEC.*`.

### Projekt wchodzi do pracy bez restartu

Wgranie projektu — z panelu (*Plik → Otwórz*) albo ze Studia przez REST
— **przebudowuje sterownik w miejscu**: karty, kanały, sterownik
magistrali, rejestr urządzeń, aparaty, komendy, użytkowników alarmówki,
moduły ze składu, opisy punktów, definicje komend, bramkę MQTT, program
logiki i panel.

Karta skasowana w Studiu zabiera swoje tagi kanałów; skasowany aparat
przestaje dawać się sterować; wymuszenia są zdejmowane. Restart został
jako droga awaryjna.

### Alarmówka

- **Dozór nocny** — linia ma flagę „czuwa nocą", strefa pokazuje tryb,
  a linia wykluczona nocą nie blokuje uzbrojenia.
- **Użytkownicy imienni** — „tylko Kowalski rozbroi magazyn". Osoby
  pochodzą z projektu, ich kody i tokeny zostają na sterowniku,
  a dziennik pisze nazwisko zamiast „Panel:Operator".
- **Sygnalizator jako stan, nie wyjście** — `SEC.SYSTEM.SIREN_ACTIVE`,
  `SIREN_TIME_LEFT`, `STROBE_ACTIVE`, `PANIC` i `REQ.SEC.SILENCE`. To, na
  którym DO wisi syrena i przez jakie blokady, rysuje inżynier.
- **Linia napadowa** (`PANIC`) — alarmuje w każdym stanie strefy,
  domyślnie cicho.
- Przycisk **Wycisz** na panelu: zatrzymuje dźwięk, nie alarm.

### Sterowanie z Home Assistanta

HAOS może uzbrajać (pełny i nocny dozór), rozbrajać, kasować alarm,
wyciszać, zmieniać nastawy zabezpieczeń i wydawać komendy aparatom.
Wymuszenia celowo zostają poza tym kanałem.

Tożsamość jedzie w wiadomości (token per osoba, wydawany na panelu),
bo Home Assistant ma jedno konto MQTT. Odrzucane: retained, stare
ponad 120 s, duplikaty, obcy token, podszycie się, za niski poziom, nie
swoja strefa. Każda odmowa to **cichy alarm**.

### Kopia zapasowa i wymiana sterownika

Pakiet `.epwbak` niesie wszystko, co istniało tylko na karcie: liczniki
łączeń, stan uzbrojenia i tryby, pamięć alarmu, wykluczenia, bity
retencyjne, dziennik audytowy, ustawienia lokalne i sam projekt.

**Nie niesie żadnych sekretów** — niesie inwentarz, kto co miał, więc
odtworzenie kończy się listą kontrolną z nazwiskami. Odtworzenie
odrzuca pakiet niewiarygodny, zanim cokolwiek zapisze, a potem
przebudowuje sterownik bez restartu. Panel, Studio i REST.

### Dwujęzyczność wszędzie

Jedno ustawienie przełącza **cztery interfejsy**: powłokę Studia,
edytor ekranów, Logic Studio i panel sterownika — a razem z Logic Studio
także **bibliotekę bloków** (70 bloków, 12 kategorii, 191 opisów) i
generowany katalog bloków w pomocy. Wybór jest zapamiętywany.

Identyfikatory IEC 61131 celowo nie są tłumaczone.

Testy pilnują, żeby to nie zgniło: tekst interfejsu, który ominął
`tr()`, oblewa test; cztery katalogi tłumaczeń muszą mieć te same klucze
i te same `{placeholdery}`; angielski katalog nie może zawierać polskich
liter.

### Pomoc

Dział pomocy w Studiu urósł z 19 ubogich tematów do 27 pełnych, z
kręgosłupem **„Jak powstaje projekt, krok po kroku"** (dwanaście
kroków). Pomoc sterownika dostała rozdział o logice, o wgrywaniu
projektu, o dozorze nocnym, użytkownikach, sygnalizatorze, sterowaniu
z HA oraz **„Nowy sterownik, krok po kroku"** i **„Wymiana padniętego
sterownika"**.

### Widok główny

Main View to **ekran osadzony w projekcie**, rysowany na żywo. Zniknął
panel pomiarowy, którego wartości produkował `random()` co 250 ms.

### Czego nadal nie ma

- **Mapowanie rejestrów Modbus** potwierdzone na sprzęcie — dziś to
  standard Modbus, nie zmierzone zachowanie kart ELA/ADA/EPM.
  Narzędzie: `runtime/tools/modbus_probe.py`.
- **Historia trendów w kopii zapasowej** — celowo: to pomiary, nie
  konfiguracja, i potencjalnie ogromne.
- **Test zabezpieczeń nie obejmuje toru ADA01** — funkcje ANSI wykonuje
  karta, czego nie da się sprawdzić wymuszeniem tagu.

---

## Wcześniej

Platforma powstała ze scalenia trzech repozytoriów 2026-09-09 (121
zmergowanych PR-ów). Historia sprzed scalenia pozostaje w archiwalnych
repozytoriach `EPW-OS`, `EPW-Logic-Studio` i `EPW-Synoptic-Editor`;
szczegółowe raporty z tamtego okresu leżą w `studio/logic/` oznaczone
jako dokumenty historyczne.
