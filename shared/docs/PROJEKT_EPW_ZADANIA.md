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

Szczegóły: SPEC, „Wersjonowanie". Nie ma jeszcze: podglądu nastaw sterownika
na żywo z zaznaczeniem różnic bez wysyłania (SPEC p. 4 listy końcowej).

---

## 6. Dług i luki znalezione przy tym zadaniu

- **Pokój (room) nie ma własnego rekordu.** Nazwa i lokalizacja pomieszczenia siedzą na ścianach (`WallElement.roomName` / `roomLocation` w Synoptic).
- **Próg ostrzegawczy licznika łączeń** (`warning_threshold`) to według SPEC nastawa, ale format nie ma dla niego pola. Zostaje w `runtime_state.json` przy rekordzie licznika, jak dotąd.
- **Ustawienia sterownika spoza formatu** trafiły do `controller.local.json`:
  - język interfejsu;
  - REST (host, port);
  - MQTT;
  - retencje historiana, dziennika i historii alarmów;
  - ostrzeżenie o rozmiarze bazy;
  - notatki serwisowe;
  - ścieżki `.epwsyn` / `.epwlogic`.

  Do rozstrzygnięcia, które z nich należą do projektu.
- **Main View — wiązanie symboli.** ZROBIONE 2026-09-15: najpierw `deviceId`
  z obiektów osadzonego ekranu (`apparatus.bind_roles_from_screens()`), reguła
  nazewnicza (`MAIN_VIEW_ROLE_DESIGNATIONS`) tylko dla symboli, których ekran nie
  rysuje. Dwa różne aparaty narysowane dla jednego oznaczenia nadal zostawiają
  symbol „nie skonfigurowany".
- **Renderer ekranów — co jeszcze nie jest na żywo** (etap pierwszy, 2026-09-15):
  - kolor przewodów według sieci: `NetResolver.ts` (328 linii, graf po całym
    schemacie) nie jest przeniesiony — przewód rysuje się w stanie z pliku;
  - animacja obrotu (wentylator): eksport niesie pozę bazową, nie wie, która
    część się obraca; mruganie i „marsz" kreski działają;
  - ściany rysowane jako pasy bez cieniowania edytora, pokoje bez podłogi;
  - `clipFunc` (2 symbole zbiorników) nie jest eksportowany — zbiornik rysuje
    się bez przycięcia poziomu;
  - eksport trzeba powtórzyć po zmianie biblioteki symboli
    (`studio/synoptic/tools/geometry_export`), test runtime to wykrywa.
- **Sterownik Modbus — założenia do potwierdzenia na sprzęcie:** mapowanie
  kanał n → adres n-1, DI przez FC2, odczyt zwrotny DO przez FC1 (wyłączany
  `read_back_outputs`), AI jako 16-bit bez znaku (`ai_signed`). Bez pomiaru na
  prawdziwych modułach ELA/ADA/EPM to jest standard Modbus, nie potwierdzone
  zachowanie tych kart. Narzędzie do tego pomiaru: `runtime/tools/modbus_probe.py`
  (2026-09-17), np. `python tools/modbus_probe.py --rtu COM3 --unit 1 --di 16 --ai 4`.
- **Migracja obecnego `project.json`:**
  - 16 punktów analogowych trafiło na kartę `AI1` z **pustym modelem**, bo moduł jest nieznany — do uzupełnienia w Studio;
  - 64 rekordy liczników łączeń, w tym 5 niezerowych, są pod płaskimi nazwami `DI1..DI64` sprzed adresacji kartowej;
  - projekt nie ma karty DI, więc nie zostały przeniesione;
  - po dodaniu karty w Studio: `migrate_project_json.py --flat-di-card <id karty>` (stary plik nadal jest).
- **Zabezpieczenia elektryczne w runtime** nie mają trwałości poza projektem.
  - Wartości etapów pochodzą z `projekt.epw`, a etap, którego projekt nie wymienia, ma wartość domyślną z katalogu ADA01.
  - Test weryfikacji zabezpieczeń dostaje id aparatu z listy aparatów projektu mających wyjście i punkt zwrotny.
- **Wgranie projektu nie przebudowuje działającego sterownika** — potrzebny restart (p. 3).
