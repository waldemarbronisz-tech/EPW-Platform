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

⚠️ **Do przepięcia przy osadzaniu ekranów i logiki w projekcie.**

`projekt.epw` nie zawiera jeszcze ekranów ani logiki. Kontrola z SPEC („logika albo ekrany odwołują się do sygnałów modułu, którego nie ma w składzie") czyta więc **dwa pliki, które runtime wczytuje dziś**. Ich ścieżki są w `controller.local.json`:

- `logic_project` — skompilowana logika (`EPW_RUNTIME_LOGIC`, eksport `.epwlogic`), którą `LogicEngine` ładuje przy starcie;
- `synoptic_project` — plik ekranu `.epwsyn`.

Kod: `runtime/epw_os/core/composition_check.py`.
- Źródła wskazuje jedna funkcja `_sources()`. Przy osadzaniu wystarczy podmienić ją na sekcje `screens` i `logic` z projektu.
- Reguły przypisania sygnałów do modułów zostają bez zmian:

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
   - zmiana działa **po restarcie**, bo tagi, moduły i strony budują się z projektu raz, przy starcie.
2. **Ręcznie:** skopiowanie pliku do `runtime/projekt.epw` (albo wskazanie go przez `EPW_PROJECT_FILE`) i restart.
3. **Odczyt ze sterownika:** `GET /api/v1/project` zwraca:
   - nazwę, opis, autora i daty;
   - `revision` i `modified_by`;
   - skład i liczności.

   Tego Studio potrzebuje przed wysłaniem projektu, żeby zatrzymać się, gdy sterownik ma nowszą rewizję.
4. **Ściągnięcie ze sterownika:** *Plik → Eksport* zapisuje `projekt.epw` dokładnie w postaci, w jakiej sterownik z nim pracuje, razem z nastawami zmienionymi na panelu.

---

## 4. ZADANIE DO ZGŁOSZENIA: „Studio osadza ekrany, logikę i settings_hash w projekt.epw"

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
  symbole w edytorze) i tryb wymuszania w rejestrze punktów. Zostaje:
  raport testu zabezpieczeń (pomiar czasu zadziałania).
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
  przez prawdziwy REST → żądanie restartu. Na sprzęcie zostaje tylko potwierdzenie
  mapowania (`modbus_probe.py`).
- **Zabezpieczenia elektryczne w runtime** nie mają trwałości poza projektem.
  - Wartości etapów pochodzą z `projekt.epw`, a etap, którego projekt nie wymienia, ma wartość domyślną z katalogu ADA01.
  - Test weryfikacji zabezpieczeń dostaje id aparatu z listy aparatów projektu mających wyjście i punkt zwrotny.
- **Wgranie projektu nie przebudowuje działającego sterownika** — potrzebny restart (p. 3).
