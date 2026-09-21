# projekt.epw w runtime — jak to dziś działa, co zostało do zrobienia

Stan po zadaniu „runtime czyta projekt.epw" (gałąź `feature/runtime-reads-project`).
Kontrakt formatu: `SPEC_PROJEKT_EPW.md`. Ten dokument opisuje, jak runtime
się do niego dostroił, na czym opierają się rozwiązania tymczasowe i co
trzeba zgłosić jako osobne zadania.

---

## 1. Trzy pliki sterownika

| Plik | Co w nim jest | Kto pisze |
|---|---|---|
| `runtime/projekt.epw` | projekt: karty, punkty, aparaty, skład, alarmówka, zabezpieczenia | Studio; runtime tylko nastawy |
| `runtime/runtime_state.json` | stan: liczniki łączeń, uzbrojenie, wykluczenia, pamięć alarmu, nadzór linii, ostatni ekran | wyłącznie runtime |
| `runtime/controller.local.json` | ustawienia tego sterownika, których format projektu nie ma (patrz p. 6) | wyłącznie runtime |

- Oba pliki lokalne są w `.gitignore`.
- Stary `runtime/project.json` został jako kopia. Runtime go nie czyta.
- Skrypt jednorazowego importu: `runtime/tools/migrate_project_json.py`.
- Czytnik formatu jest jeden: `shared/project_format.py`. Studio i runtime korzystają z niego przez cienkie przekierowania.
- Inny plik projektu wskazuje zmienna `EPW_PROJECT_FILE`. Pliki stanu i ustawień leżą wtedy obok niego.

Zapis z panelu:
- Nastawa trafia do `projekt.epw`: `revision` + 1, `modified_by = "panel"`, wpis `PROJECT_SETTING_CHANGED` w dzienniku.
- Zmiana struktury jest odrzucana i też trafia do dziennika (`PROJECT_STRUCTURE_CHANGE_REFUSED`).
- Liczniki i uzbrojenie nigdy nie dotykają pliku projektu.

---

## 2. Kontrola składu urządzenia — NA CZYM SIĘ DZIŚ OPIERA

Kontrola z SPEC („logika albo ekrany odwołują się do sygnałów modułu,
którego nie ma w składzie") czyta **ekrany i logikę osadzone w
`projekt.epw`** (sekcje `screens` i `logic_runtime`). Pliki
`logic_project` / `synoptic_project` z `controller.local.json` zostały
jako zapas dla projektu zapisanego, zanim osadzanie powstało — osadzony
dokument zawsze wygrywa z plikiem tego samego rodzaju.

Kod: `runtime/epw_os/core/composition_check.py`, funkcja `_sources()`.
- Reguły przypisania sygnałów do modułów:

| Moduł | Sygnały |
|---|---|
| `intrusion` | `Security.*` |
| `protection_process` | `Process.<id>.Exceeded` |
| `analog_inputs` | adresy `<karta>.AI.<n>` |

Rozjazd oznacza:
- komunikat przy starcie w oknie panelu (en/pl);
- alarm `COMPOSITION_<MODUŁ>_<LOGIC|SCREEN>`;
- wpis w logu.

Moduł spoza składu w ogóle nie jest tworzony: nie ma obiektu, wątków ani tagów.

---

## 3. Jak projekt trafia na sterownik (dziś)

1. **Na miejscu, z panelu:**
   - *Plik → Otwórz* (poziom Engineer) wgrywa wskazany `.epw`;
   - plik jest najpierw sprawdzany wspólnym czytnikiem, a zły jest odrzucany z powodem;
   - poprzedni plik zostaje jako `projekt.epw.bak`, a zdarzenie trafia do dziennika;
   - panel pyta, czy przebudować sterownik teraz — i **przebudowuje go bez
     restartu** (`EPWCore.reload_project()`, p. 3a). Odmowa zostawia plik na
     następny start, tak jak było wcześniej.
2. **Ręcznie:** skopiowanie pliku do `runtime/projekt.epw` (albo wskazanie go przez `EPW_PROJECT_FILE`) i restart.
3. **Odczyt ze sterownika:** `GET /api/v1/project` zwraca:
   - nazwę, opis, autora i daty;
   - `revision` i `modified_by`;
   - skład i liczności.

   Tego Studio potrzebuje przed wysłaniem projektu, żeby zatrzymać się, gdy sterownik ma nowszą rewizję.
4. **Ściągnięcie ze sterownika:** *Plik → Eksport* zapisuje `projekt.epw` dokładnie w postaci, w jakiej sterownik z nim pracuje, razem z nastawami zmienionymi na panelu.

---

## 3a. Przeładowanie projektu bez restartu — ZROBIONE 2026-09-20

Polecenie właściciela: „działaj z tym". Do tej pory na żywo dało się
wymienić wyłącznie **program logiki**; reszta budowała się z projektu raz,
przy starcie. `EPWCore.reload_project()` przebudowuje całą resztę.

**Co jest przebudowywane** — dokładnie to, co `startup()` buduje z projektu,
w tej samej kolejności i **tymi samymi pomocnikami** (ta sama para
start/stop modułu, ten sam `_configure_io_driver()`, te same definicje
komend), żeby istniał jeden opis „jak projekt staje się sterownikiem", a nie
dwa, które mogą się rozjechać:

karty i ich kanały → sterownik magistrali → rejestr urządzeń → aparaty i
ich powiązania z Widokiem Głównym → symulowana instalacja → użytkownicy
alarmówki → moduły ze składu → opisy tagów i rejestr punktów → definicje
komend → bramka MQTT → program logiki → sprawdzenie składu.

**Co NIE jest ruszane** — wszystko, czego projekt nie posiada: baza i
historian, sam menedżer sterowników, `safety_kernel`, łącze MQTT, REST,
dziennik audytowy, poziom dostępu, na którym ktoś jest zalogowany. To
przeżywa projekty.

**Cztery rzeczy, które naiwne „domerguj" robi źle** — i dlatego mają
własne metody:

| Problem | Odpowiedź |
|---|---|
| karta skasowana w Studiu zostawiała swoje tagi kanałów na zawsze | `TagManager.reconfigure()` — jedyna droga, którą tag kanału może **zniknąć**; usuwa dokładnie to, co poprzednie `configure()` stworzyło, a czego ta lista kart już nie tworzy |
| aparat skasowany w Studiu dalej dawał się sterować (`load_definitions()` merguje po kluczu) | `CommandManager.clear_definitions()` przed ponownym wczytaniem |
| karta znikała z projektu, ale zostawała w rejestrze urządzeń i wisiała na timeoucie | `DeviceManager.unregister_device()` |
| `register_driver()` podmienia referencję po cichu, więc poprzedni sterownik magistrali dalej odpytywałby tę samą szynę własnym wątkiem | `DriverManager.unregister_driver()` — zatrzymuje i zapomina; nowy startuje pojedynczo, bo `start_all()` uruchomiłoby drugi wątek w każdym już działającym sterowniku |

**Wymuszenia są zdejmowane na początku** — wymuszenie przypina tag, którego
nowy projekt może w ogóle nie mieć.

**Panel** przebudowuje się tak samo, jak przy zmianie języka i zmianie
składu: `main.py` słucha zdarzenia `project_reloaded` i woła
`rebuild_window()`. Strony i nawigacja też budują się z projektu i żadnego z
tych trzech przypadków nie da się bezpiecznie połatać w miejscu.

**Poziom Engineer, wpis w dzienniku** (`PROJECT_RELOADED`). Odrzucony plik
zostawia w pracy poprzedni projekt.

**REST:** `POST /api/v1/project/install` domyślnie przeładowuje
(`?reload=false` wgrywa na następny start; restart nie jest już planowany,
kiedy przeładowanie się udało) i odpowiada polem `reloaded` — czy sterownik
naprawdę pracuje już według przysłanego projektu.

Dowód: `runtime/epw_os/tests/test_project_hot_reload.py`.

---

## 3b. Kopia zapasowa sterownika i wymiana egzemplarza — ZROBIONE 2026-09-20

Projekt był bezpieczny (Studio, git, REST). Wszystko, co należy do
**egzemplarza**, istniało wyłącznie na jego karcie: liczniki łączeń,
stan uzbrojenia i tryby, wykluczenia, pamięć alarmu, nadzór linii, bity
retencyjne logiki, dziennik audytowy, ustawienia lokalne. Padnięta karta
= odtwarzanie tego z pamięci, bez procedury.

**Pakiet** (`.epwbak`, gzip+JSON, marker formatu, wersja schematu, suma
kontrolna) niesie: projekt (żeby był samowystarczalny), `runtime_state.json`,
`controller.local.json`, dziennik audytowy i **inwentarz sekretów**.

**Sekretów nie niesie — nigdy.** Ani haszy PIN-ów, ani kodów
użytkowników alarmówki, ani tokenów zdalnych i API, ani hasła brokera.
Uzasadnienie, bo to jest rozstrzygnięcie, a nie skrót: pakiet to plik,
który opuszcza obiekt — laptop, mail, pendrive w samochodzie. PIN ma
cztery cyfry, więc jego hasz jest o jedną tablicę od bycia PIN-em.
Szyfrowanie pakietu odpowiedziałoby na to, ale sterownik nie ma
biblioteki kryptograficznej, a dokładanie jej po to, żeby rozwiązać
problem, którego można uniknąć, jest złym kompromisem. Więc się go
unika.

Zamiast sekretów jedzie **inwentarz**: kto miał kod, kto miał token, czy
tokeny API i hasło brokera były ustawione. Odtworzenie zamienia to na
**listę kontrolną z nazwiskami**. Nadanie pięciu kodów z listy to
dziesięć minut; odzyskanie czterech lat liczników jest niemożliwe — i to
jest cały argument.

**Historii trendów też nie niesie** (pomiary, nie konfiguracja,
potencjalnie ogromne). Sterownik bez trendów pracuje; sterownik bez
stanu uzbrojenia kłamie o budynku.

**Odtworzenie**: pakiet niewiarygodny (format, wersja schematu, suma
kontrolna) jest odrzucany, **zanim cokolwiek zostanie zapisane** — nigdy
do połowy. Pliki zapisuje `controller_backup`, a do pracy wprowadza je
`reload_project()` — ta sama jedyna droga, którą idzie każde wgranie
projektu, więc odtworzenie nie wymyśla drugiego sposobu uruchamiania
projektu. Bez restartu.

**Ustawienia lokalne są scalane, nie nadpisywane**: adres REST, sterownik
wejść/wyjść i ścieżki plików opisują sprzęt, na którym zamiennik
pracuje, a nie ten, który padł.

**Stan uzbrojenia wraca taki, jaki był** — ta sama zasada, co przy
restarcie sterownika („uzbrojona wstaje uzbrojona"), z wpisem do
dziennika.

| Droga | Gdzie |
|---|---|
| Panel | Ustawienia → Kopia zapasowa sterownika... / Odtwórz z kopii zapasowej... |
| Studio | Sterownik → Kopia zapasowa sterownika |
| REST | `GET /api/v1/controller/backup`, `POST /api/v1/controller/backup/inspect`, `POST /api/v1/controller/restore` |

Wszystko na poziomie Engineer, wszystko w dzienniku.

Dowód: `runtime/epw_os/tests/test_controller_backup.py` (co pakiet
niesie i czego nie niesie), `test_controller_backup_api.py` (pełna
wymiana egzemplarza przez REST, z dowodem, że kod z oryginału **nie**
działa na zamienniku, a stan uzbrojenia **wraca**),
`runtime/gui_smoke/test_controller_backup_panel.py` (panel przy szafie).

Procedura wymiany krok po kroku: pomoc sterownika, rozdział „Kopia
zapasowa i wymiana".

---

## 4. „Studio osadza ekrany, logikę i settings_hash w projekt.epw" — ZROBIONE

> **Stan 2026-09-15:** sekcje `screens` / `logic` / `logic_runtime` — ZROBIONE
> (zapis/odczyt w Studio, runtime czyta je z projektu, `composition_check._sources()`
> przepięte, ścieżki plików tylko jako zapas). Main View po `deviceId` — ZROBIONE
> (`apparatus.bind_roles_from_screens()`). Renderer ekranów w runtime — ZROBIONE,
> etap pierwszy (strona *Synoptyka*, `shared/symbols/geometry.json`; patrz SPEC
> „Runtime rysuje osadzony ekran"). Sterownik Modbus w runtime — ZROBIONE
> (`drivers/modbus_driver.py`, ustawienie `io_driver` w `controller.local.json`).
> Rejestr aparatów Studio ↔ Synoptic — ZROBIONE (most dodający, jak karty).
> `settings_hash` — ZROBIONE 2026-09-17 (p. 5).

**Warunek wstępny renderera ekranów i pełnego wersjonowania nastaw.**

Zakres:
- sekcje `screens` (obiekty jak w `.epwsyn`), `logic` (jak `.epwlogic.runtime.json`) oraz pole `settings_hash` w formacie i w zapisie Studio;
- runtime czyta `screens`/`logic` z projektu; `composition_check._sources()` przepięte na te sekcje (p. 2);
- Main View: symbole biorą aparat z `deviceId` obiektów ekranu zamiast reguły nazewniczej z p. 6;
- `settings_hash` liczony z nastaw; Studio porównuje go przed wysłaniem projektu (SPEC, „Wersjonowanie").

## 4a. Runtime WYKONUJE logikę — ZROBIONE 2026-09-19

Do tego zadania sterownik logikę tylko **trzymał**: `LogicEngine` sprawdzał
marker formatu i odpowiadał „czy cokolwiek jest skonfigurowane", a graf
blokad nigdy nie był liczony (mówił to własny komentarz w kodzie: „In a
real engine, we'd evaluate the interlock graph").

Teraz skan naprawdę działa, na tym samym silniku i tej samej bibliotece
bloków, co symulacja w Logic Studio (`shared/logic/`). Szczegóły —
odmowy ładowarki, granice wobec trybu szkoleniowego i wymuszeń,
odwzorowanie sygnałów `SYS.*` i `SEC.*` i `REQ.SEC.*` oraz trwałość bitów
retencyjnych — opisuje osobny dokument:
**`LOGIKA_W_RUNTIME.md`**.

## 5. Wysyłanie projektu na sterownik przez REST — ZROBIONE 2026-09-17

- token Engineer: `GET /api/v1/project/file`, `POST /api/v1/project/install`;
- `settings_hash` w nagłówku (`project_format.settings_hash()`), porównanie w Studio
  przed wysłaniem, odmowa 409 przy zmianie rewizji na sterowniku w międzyczasie;
- rozjazd nastaw: `GET /api/v1/project/settings` + tabela w Studio
  (`SettingsDiffDialog`);
- restart: `EPWCore.request_restart()` → wyjście kodem 3 → `systemd Restart=on-failure`;
  powrót do `.bak` przy odrzuconym starcie (`projekt.epw.pending`, problem startowy
  `PROJECT_ROLLED_BACK`).

Szczegóły: SPEC, „Wersjonowanie". Podgląd nastaw sterownika na żywo z
zaznaczeniem różnic — ZROBIONE 2026-09-17 (panel *Sterownik*, grupa „Nastawy
sterownika (na żywo)": pobranie / odświeżanie co 5 s, tabela nastawa / Studio /
sterownik z podświetleniem różnic, „Przyjmij nastawy sterownika do projektu"
przez `project_format.apply_settings_snapshot()`).

---

## 6. Dług i luki znalezione przy tym zadaniu

- **Pokój (room)** — ZROBIONE 2026-09-17: rekord `rooms: [{id, name, location}]`
  w dokumencie ekranu, każda ściana pokoju wskazuje go przez `roomId`
  (`elements/RoomElement.ts`, reguły w `project/Rooms.ts`: jeden rekord na
  łańcuch ścian, wklejony pokój dostaje własny, kasowanie ścian usuwa rekord,
  stary plik z `roomName`/`roomLocation` na ścianach migruje przy otwarciu).
  Runtime rysuje podłogi zamkniętych pętli ścian w materiale ekranu, ściany
  jak edytor — pseudo-3D wytłoczenie (`gui/synoptic/walls3d.py`, port
  `WallGeometry.ts`/`WallLayer.tsx`: pas ściany z mitrowanymi narożnikami,
  ściany dalekie wytłoczone w górę z cieniowaniem od kierunku światła,
  bliskie przycięte do 30 % wysokości, nakrywa, listwa, cień na podłodze)
  i etykietę „nazwa - lokalizacja" z rekordu (`gui/synoptic/rooms.py`).
  Otwory (drzwi, okna) nie wycinają ściany — jak dotąd w edytorze.
- **Próg ostrzegawczy licznika łączeń** — ZROBIONE 2026-09-17: pole
  `Point.warning_threshold` (punkt DI) w formacie, kolumna w rejestrze punktów
  Studio, część `settings_hash`; runtime zasila nim rekord licznika (projekt
  wygrywa ze stanem), zmiana z panelu wraca do `projekt.epw` jak każda nastawa
  (`switching_counter_settings` w widoku projektu). Same liczniki nadal tylko
  w `runtime_state.json`.
- **Ustawienia sterownika spoza formatu** — ROZSTRZYGNIĘTE 2026-09-18.
  Do projektu (jako nastawy: panel może zmienić z wpisem do dziennika,
  rewizja +1 „panel", Studio widzi różnicę i może przyjąć):
  - **MQTT** (`mqtt`, `project_format.MqttConfig`; bez hasła — to zostaje
    w lokalnym pliku sterownika), panel Studio „Integracja MQTT";
  - **notatki serwisowe** (`service_notes`, per aparat, dziennik
    nieusuwalny; każdy wpis na panelu trafia do `projekt.epw`), panel
    Studio „Notatki serwisowe" (tylko do odczytu).

  Zostają lokalne w `controller.local.json` (opisują egzemplarz
  sterownika, nie instalację): język interfejsu, REST (host, port),
  retencje historiana, dziennika i historii alarmów, ostrzeżenie o
  rozmiarze bazy, sterownik I/O, ścieżki `.epwsyn` / `.epwlogic`. Studio
  czyta je tylko do odczytu przez `GET /api/v1/controller/settings`
  (panel Sterownik → „Ustawienia lokalne sterownika") — nic na sterowniku
  nie jest niewidoczne ze Studio.
- **Obiekt z wielu sterowników** — ZROBIONE 2026-09-18: plik obiektu
  `obiekt.epwsite` (`studio/shell/site_format.py`), lista urządzeń nad
  drzewem, jeden projekt na sterownik, przełączanie z zachowaniem edycji.
  Krok drugi tego samego dnia — **powiązania obiektu**: punkt jednego
  sterownika dostępny u drugiego jako tag `Link.<Id>.In<n>` przez MQTT
  (źródło publikuje pod `<prefiks>/tag/<ścieżka>/state`, Studio wpisuje
  mapowanie przychodzące do `mqtt.link_in` celu, włącza MQTT i nadaje
  prefiks tam, gdzie ich nie było; usunięcie sterownika zabiera jego
  powiązania). Runtime bez zmian — `link_in` już był. Panel „Powiązania
  obiektu" pod KONFIGURACJA. Nie ma adresowania między projektami na
  ekranach (`EntryGate:ELA1.DI.1`) — ekran celu wiąże symbol z tagiem
  `Link.*` jak z każdym innym.
- **Wymuszanie stanów ze Studio i żywe stany przy projektowaniu** —
  ZROBIONE 2026-09-18 (SPEC „Wymuszanie stanów" i „Co jeszcze daje ten
  kanał"): `core/force_manager.py` + `/api/v1/forces` (Engineer, audyt,
  heartbeat 15 s, zdjęcie przy zamknięciu), wskaźnik na pasku panelu,
  w Studio przełącznik „Na żywo" (rejestr punktów, karty „Odpowiada",
  symbole w edytorze) i tryb wymuszania w rejestrze punktów. Raport testu
  zabezpieczeń: osobny wpis niżej.
- **Test zabezpieczeń („wewnętrzny Omicron")** — ZROBIONE 2026-09-18 (SPEC
  „Wymuszanie stanów — Powiązanie"): `core/protection_test.py` (test
  zabezpieczenia procesowego: wymuszenie ponad próg, czas zadziałania vs
  zwłoka, czas skasowania; test aparatu: komenda przez CommandManager, czas
  sprzężenia, powrót), REST `/api/v1/protection-tests` (Engineer), raporty
  na sterowniku + audyt, Studio: Sterownik → Test zabezpieczeń (lista,
  start, śledzenie, CSV).
- **Zerowanie liczników łączeń ze Studio** — ZROBIONE 2026-09-18:
  `GET /api/v1/counters` (stan wszystkich liczników) i
  `POST /api/v1/counters/<tag>/reset` (token Engineer, ta sama ścieżka co
  menu Engineer na panelu, wpis `COUNTER_RESET` w dzienniku); panel
  Sterownik ma grupę „Liczniki łączeń" z „Zeruj wybrany" / „Zeruj
  wszystkie". Strona DI odświeża liczniki co 2 s, więc zerowanie z zewnątrz
  jest widoczne od razu.
- **Main View — wiązanie symboli.** ZROBIONE 2026-09-15: najpierw `deviceId`
  z obiektów osadzonego ekranu (`apparatus.bind_roles_from_screens()`), reguła
  nazewnicza (`MAIN_VIEW_ROLE_DESIGNATIONS`) tylko dla symboli, których ekran nie
  rysuje. Dwa różne aparaty narysowane dla jednego oznaczenia nadal zostawiają
  symbol „nie skonfigurowany".
- **Renderer ekranów — etap drugi (2026-09-17):** kolor przewodów według sieci
  ZROBIONY (`gui/synoptic/net_resolver.py`, port `NetResolver.ts`: sieć zasilana
  z punktu granicznego SOURCE albo z zacisku OUT aparatu, którego potwierdzenie
  na żywo mówi „załączony"; kropki węzłów jak w edytorze; symbole wodne mają
  wariant „sieć aktywna"); animacja obrotu ZROBIONA (eksport oznacza obracaną
  część `$animate_rotation`, znalezioną przez drugi przebieg z przesuniętym
  stanem). Ściany i podłogi pokoi — ZROBIONE 2026-09-17 (patrz „Pokój" wyżej),
  od tego samego dnia z pseudo-3D wytłoczeniem edytora (`walls3d.py`).
  `clipFunc` (2 symbole zbiorników) — ZROBIONE 2026-09-17: eksport uruchamia
  funkcję na kontekście nagrywającym (`rect`/`arc`/`moveTo`-`lineTo`) i
  zapisuje kształty jako `clip` węzła, painter przecina nimi obszar
  rysowania — poziom w zbiorniku jest przycięty do jego wnętrza. Otwory
  drzwi, okien i bram wycinają ścianę i jej wytłoczenie jak w edytorze
  (port `WallOpenings.ts`, 2026-09-18). Eksport geometrii: 0 ostrzeżeń
  (struktura zależna od pól, jak wiersze `scada.meter`, jest notatką, nie
  ostrzeżeniem). Zostaje:
  - eksport trzeba powtórzyć po zmianie biblioteki symboli
    (`studio/synoptic/tools/geometry_export`), test runtime to wykrywa.
- **Sterownik Modbus — założenia do potwierdzenia na sprzęcie:** mapowanie
  kanał n → adres n-1, DI przez FC2, odczyt zwrotny DO przez FC1 (wyłączany
  `read_back_outputs`), AI jako 16-bit bez znaku (`ai_signed`). Bez pomiaru na
  prawdziwych modułach ELA/ADA/EPM to jest standard Modbus, nie potwierdzone
  zachowanie tych kart. Narzędzie do tego pomiaru: `runtime/tools/modbus_probe.py`
  (2026-09-17), np. `python tools/modbus_probe.py --rtu COM3 --unit 1 --di 16 --ai 4`.
- **Migracja obecnego `project.json`** — ZAMKNIĘTE 2026-09-18: `runtime/projekt.epw`
  dostał skład opisany przez użytkownika — `ELA1` (model ELA, STM32,
  16 DI + 8 AI, Modbus unit 1) i `ADA1` (model ADA, STM32, 16 DO + 8 AO,
  Modbus unit 2), lokalizacja `ROZ`; karta-zastępnik `AI1` z 16 pustymi
  punktami usunięta (nic się do niej nie odwoływało). Stare liczniki
  `DI1..DI64` (5 niezerowych, ślady testów z 1 września) nie zostały
  przeniesione — liczniki zaczynają od zera. Kopia poprzedniego pliku:
  `runtime/projekt.epw.bak-2026-09-18`. `migrate_project_json.py` kieruje
  odtąd `mqtt` i `service_notes` ze starego pliku do projektu, nie do
  `controller.local.json`.
- **Sprawdzenie softwarowe bez sprzętu (2026-09-17):** `runtime/tools/modbus_sim.py`
  udaje karty projektu po Modbus TCP (wejścia z konsoli, `--mirror` = potwierdzenie
  z cewki); symulowana instalacja (`simulation/simulated_plant.py`) odpowiada na
  aparaty projektu w trybie symulatora (MAINTAINED, PULSE, PULSE_TOGGLE);
  `test_software_commissioning.py` przechodzi całą pętlę: magistrala → strona
  Synoptyka → kliknięcie → cewka → potwierdzenie → wysyłka projektu ze Studio
  przez prawdziwy REST → **przebudowa sterownika w miejscu** (p. 3a; jeden wątek
  odpytujący magistralę, żadnego restartu). Na sprzęcie zostaje tylko potwierdzenie
  mapowania (`modbus_probe.py`).
- **Zabezpieczenia elektryczne w runtime** nie mają trwałości poza projektem.
  - Wartości etapów pochodzą z `projekt.epw`, a etap, którego projekt nie wymienia, ma wartość domyślną z katalogu ADA01.
  - Test weryfikacji zabezpieczeń dostaje id aparatu z listy aparatów projektu mających wyjście i punkt zwrotny.
- **Wgranie projektu przebudowuje działający sterownik** — ZROBIONE 2026-09-20,
  p. 3a. Restart został jako droga awaryjna (`?reload=false&restart=true`), nie
  jako normalna procedura.
- **Sterowanie z Home Assistanta przez MQTT** — ZROBIONE 2026-09-20.
  Łącze MQTT przestało być tylko podglądem: HAOS może uzbrajać alarmówkę
  (pełny i nocny dozór), rozbrajać, kasować alarm, zmieniać nastawy
  zabezpieczeń i wydawać komendy aparatom. Wymuszenia **celowo** zostają
  poza tym kanałem. Rozstrzygnięcia i format wiadomości opisuje
  `MQTT_STEROWANIE.md`; w skrócie:
  - komendy sprawdza **osobna bramka** (`core/remote_commands.py`), a
    `mqtt_manager.py` nadal nie zna żadnej ścieżki sterowania — dostaje
    callback i tyle;
  - **tożsamość jedzie w wiadomości**, bo Home Assistant ma jedno konto
    MQTT i broker nie odróżni dwóch osób; token per osoba, hash w pliku
    sterownika, wydawany na panelu (Ustawienia → Użytkownicy alarmówki),
    pokazywany raz;
  - **token to nie kod na klawiaturę** — wyciek z HA nie może otwierać
    panelu przy szafie; unieważnienie tokenu nie rusza kodu;
  - odrzucane: retained (odtwarzane po każdym restarcie), starsze niż
    120 s, duplikaty `id` (wykonanie pomijane, odpowiedź powtórzona),
    obcy token, podszycie się pod kogoś innego, za niski poziom, nie
    swoja strefa. Każda odmowa wygląda jak włam → **cichy alarm**
    `REMOTE_COMMAND_REFUSED`, który przez MQTT staje się powiadomieniem
    w HA;
  - uprawnienia i wykonanie idą przez **te same managery co panel**
    (alarmówka, CommandManager), więc safety kernel, blokady logiki,
    wymuszenia i tryb szkoleniowy działają bez zmian;
  - granica, która zostaje: kto przejmie HAOS, wyśle komendę tokenem,
    który tam leży. Dlatego z zewnątrz łączysz się z HAOS (VPN/Nabu
    Casa), a broker zostaje w LAN — sterownik ostrzega przy starcie, gdy
    broker nie jest lokalny, i osobno gdy przy tym nie ma TLS.
- **Main View bez wymyślonych pomiarów** — ZROBIONE 2026-09-20 (polecenie:
  „main view ma mieć tylko obraz z synoptic - tam umieszczamy wizualizację
  pomiarów"). Strona głównego widoku była ręcznie narysowaną bramą wjazdową
  z panelem pomiarowym, którego napięcia, prądy, moc i częstotliwość
  produkował timer co 250 ms przez `random()`, ze sprzężeniem zwrotnym
  udającym 95% skuteczności, plus dziewięć wartości `Cabinet.*` (temperatura
  w szafie, wilgotność, drzwi, grzałka, wentylator…), których nie pisał
  żaden czujnik. Teraz Main View to **ekran osadzony w projekcie**,
  rysowany na żywo, z własnym selektorem, gdy projekt niesie kilka ekranów.
  Pomiar trafia do operatora tą samą drogą co każda inna wartość: narysowany
  na ekranie w edytorze, związany z realnym punktem. Usunięte razem ze
  stroną: zestaw rysunkowy (przewód, szyna, wyłącznik, stycznik,
  transformator, wskaźnik cyfrowy) i cztery okna, których nic poza nią nie
  używało. Notatki serwisowe i liczniki łączeń są nietknięte — sięga się po
  nie ze stron WE/WY.
- **Alarmówka: dozór nocny i użytkownicy** — ZROBIONE 2026-09-20 (polecenie:
  „alarmy nocne, alarmy częściowe, stopnie dostępu… tylko jakiś jeden
  użytkownik może rozbroić daną strefę").
  - **Dozór nocny (częściowy)**: `ArmMode.NIGHT`. Strefa uzbrojona nocą jest
    pilnowana wyłącznie przez linie z flagą `active_at_night` — zwykle obwód
    zewnętrzny czuwa, czujki ruchu wewnątrz nie. Flaga stoi **przy linii**
    (`shared/project_format.py`), nie jako druga lista linii przy strefie:
    jedno miejsce do sprawdzenia i nie ma jak się rozjechać. Linia
    całodobowa i awaria linii alarmują niezależnie od trybu. Linia sprzed
    tej zmiany czuwa nocą — stary projekt uzbrojony nocą chroni dokładnie
    tyle, co pełny, nigdy mniej. Tryb jest zapisywany razem z uzbrojeniem
    (`runtime_state.json`), więc po zaniku zasilania strefa wraca w tym
    trybie, w którym ją zostawiono.
  - **Użytkownicy** (`intrusion.users` w projekcie): osoba, poziom, który
    daje jej własny kod, i strefy, które może obsługiwać (pusta lista =
    wszystkie). Trzy poziomy dostępu nie potrafiły odpowiedzieć „tylko
    Kowalski rozbroi magazyn", bo dwóch operatorów to dla nich ten sam
    Operator. **Kod nie jest częścią projektu** — leży w pliku dostępu
    sterownika (gitignore), pod id użytkownika; użytkownik istnieje, gdy
    projekt wyląduje, i loguje się, gdy ktoś ustawi mu kod **na panelu**.
    Kod w kartotece = identyfikacja osoby (jak w prawdziwej centrali), więc
    dziennik pisze „Kowalski rozbroił strefę", a nie „Panel:Operator".
    Odmowa (nie ta strefa, konto wyłączone, nieznany kod) też idzie do
    dziennika i historii alarmowej.
  - **Gdzie się to konfiguruje**: Studio → Alarmówka → *Użytkownicy* (kto,
    poziom, strefy, aktywny) i *Linie → Dozór nocny* (czy linia czuwa nocą).
    Panel: przycisk „Uzbrój (noc)" przy strefie, która ma co wykluczyć, a
    stan strefy pokazuje tryb.
  - **SEC**: `REQ.SEC.ARM_ALL_PARTIAL` przestaje być nieobsłużone — uzbraja
    wszystkie strefy nocą; `ARMED` wymaga teraz uzbrojenia **pełnego**
    wszystkich stref, a `ARMED_PARTIAL` obejmuje też „uzbrojone, ale nocą".
    `SIREN_*`, `STROBE_*` i `PANIC` są obsłużone od 2026-09-20 (p. 3a
    tego samego dnia — sygnalizator jako stan, linia napadowa).
- **Brak kart a edytory** — ZROBIONE 2026-09-19 (zgłoszenie: „nie dodano kart DI/DO").
  Blok wymagający fizycznego zacisku, wstawiony w projekcie bez karty, dawał
  pustą listę adresów i żadnego wyjaśnienia — powód pojawiał się dopiero przy
  kompilacji. Teraz mówi to jedno miejsce (`logic_studio/core/io_availability.py`):
  pole Address pokazuje „(no DI channels in this project)" i po kliknięciu
  tłumaczy, gdzie dodać kartę (w Studio: Configuration → I/O Cards; samodzielne
  Logic Studio: Project Settings), a upuszczenie takiego bloku pisze to na pasku
  stanu i do zakładki Warnings (celowo nie modalnie — dziesięć bloków to
  dziesięć okien). W Synoptyce ostrzeżenie stoi przy samym polu, obok „+ Card".
  Przy okazji znalezione i naprawione dwie rzeczy, które to zgłoszenie odsłoniło:
  - **logika w Studiu w ogóle się nie kompilowała** — widok kompilacji
    (`_ExpandedProjectView`) nie przenosił mostkowanych kart, więc walidator
    odrzucał każdy adres komunikatem „Card 'ELA1' does not exist in the project"
    o karcie, która istnieje;
  - **punkty analogowe nie były mostkowane do edytora logiki** — listy adresów
    AI/AO w Studiu były zawsze puste, niezależnie od kanałów kart; teraz
    `LogicPanel.sync_cards_from_studio()` przenosi też punkty (z zakresem
    inżynierskim i jednostką), a eksport runtime niesie ich rejestr.
