# Logika użytkownika w runtime — jak sterownik wykonuje to, co skompilowało Studio

Stan po zadaniu „runtime wykonuje logikę" (gałąź
`feature/logic-execution-ao-screens`). Format eksportu opisuje
`SPEC_PROJEKT_EPW.md` (sekcja `logic_runtime`); ten dokument opisuje, co
się z tym eksportem dzieje na sterowniku.

---

## 1. Jedna biblioteka bloków, jeden silnik

Biblioteka bloków, silnik wykonania i katalog sygnałów systemowych leżą
w `shared/logic/`:

| Katalog | Co w nim jest |
|---|---|
| `shared/logic/blocks/` | wszystkie typy bloków + rejestr (`BlockRegistry`) |
| `shared/logic/engine/` | `ExecutionEngine`, `CompiledProgram`, `IOProvider`, `TimeProvider` |
| `shared/logic/program_loader.py` | odtworzenie `CompiledProgram` z eksportu (strona sterownika) |
| `shared/logic/runtime_export.py` | kontrakt eksportu: marker, wersja schematu, pola objęte sumą kontrolną, suma kontrolna |
| `shared/logic/internal_bits.py`, `system_signals.py`, `system_signals_catalog.json` | rejestr sygnałów wewnętrznych i katalog `SYS.*`/`SSWIN.*` |

Logic Studio i EPW OS **wykonują ten sam kod**. To, co inżynier
przetestował na kanwie, sterownik wykonuje dosłownie — nie „zgodnie
z tym samym opisem". Własna implementacja po stronie sterownika byłaby
tylko obietnicą, że obie strony się zgadzają.

Dowód: `shared/tests/test_logic_execution_contract.py` kompiluje
przykładowe projekty kompilatorem Studia, uruchamia **oba** programy
(ten z edytora i ten odtworzony z eksportu) na tych samych wejściach
i porównuje wyjścia skan po skanie.

`shared/logic/` nie importuje `logic_studio` — sprawdzone: import
`shared.logic.blocks` bez `studio/logic` na `sys.path` działa. Dwa
miejsca, które to łamały, zostały naprawione u źródła:
- `MACRO_TYPE_PREFIX`/`macro_def_id` przeniesione do
  `shared/logic/macro_type.py` (rejestr bloków musi rozpoznać
  `macro.<def_id>`), `logic_studio.core.macros` je re-eksportuje;
- `system_signals._device_signals()` sięga po `DeviceModel` dopiero dla
  realnego projektu (dla `project=None` i tak zawsze zwracał pustą listę).

## 2. Co robi sterownik przy starcie

`EPWCore.startup()`:

1. buduje `TagIOProvider` (`runtime/epw_os/core/logic_runtime.py`) —
   wejścia z `TagManager`, wyjścia przez `DriverManager.route_command()`,
   sygnały `SYS.*` z prawdziwych managerów sterownika;
2. `LogicEngine.load_program_data()` bierze sekcję `logic_runtime`
   z `projekt.epw` (plik `.epwlogic.runtime.json` z
   `controller.local.json` zostaje jako zapas dla starszego projektu);
3. `LogicEngine.start()` uruchamia wątek skanu z `cycle_time_ms`
   programu — dopiero po starcie sterowników magistrali, żeby pierwszy
   skan miał czym dojść do sprzętu.

Stan skanu widać bez zaglądania do logu: pasek stanu panelu
(`LOGIKA: PRACA / ZATRZYMANA / AWARIA / brak`), `GET /api/v1/logic`
i panel *Sterownik* w Studio. Sam program można podmienić bez restartu:
*Projekt → Przeładuj program logiki...* albo `POST /api/v1/logic/reload`
(Engineer, do dziennika) — `EPWCore.reload_logic()` zatrzymuje skan (co
sprowadza jego wyjścia do stanu bezpiecznego), czyta projekt z dysku i
startuje na nowo. Reszta projektu nadal wymaga restartu.

Stan podsystemu `LOGIC_RUNTIME`:

| Sytuacja | Stan | Zgłoszenie startowe |
|---|---|---|
| brak logiki w projekcie i brak pliku | `DEGRADED` | — |
| dokument odrzucony (suma kontrolna, nieznany blok, niezgodne piny, nowszy schemat) | `FAULT` | `LOGIC_PROGRAM_REJECTED` |
| wczytany, ale skan nie wystartował | `FAULT` | `LOGIC_SCAN_NOT_STARTED` |
| skan działa | `RUNNING` | — |

## 3. Czego ładowarka odmawia

`shared/logic/program_loader.py` woli nie uruchomić niczego niż
uruchomić coś innego, niż skompilowano. `ProgramLoadError` leci przy:

- niezgodnej sumie kontrolnej (plik zmieniony po kompilacji),
- `schema_version` nowszym niż ten sterownik rozumie,
- typie bloku, którego biblioteka tego sterownika nie zna,
- bloku, którego liczba pinów nie zgadza się z biblioteką (program
  kompilowany na innej wersji bloków — trzeba przekompilować w Studio),
- `execution_order` wskazującym blok, którego w eksporcie nie ma.

Trzy rzeczy, które kompilator rozwiązuje z żywego projektu, sterownik
odtwarza z danych, które eksporter nosi właśnie po to: zakres bloku AI
i bloku jakości (`_resolved_range_min`/`_max`) oraz prawdziwy
identyfikator sygnału wewnętrznego (`M./MR./MW./MWR.<nazwa>`, z kopii
rejestru `internal_bits`).

## 4. Granice — logika nie ma własnej drogi do sprzętu

- Wyjścia DO/AO idą przez `DriverManager.route_command()`, czyli tę samą
  jedyną granicę co komenda operatora. **Tryb szkoleniowy** odcina
  wyjście sterowane logiką dokładnie tak samo jak komendę.
- **Wymuszenie** (force) na wyjściu blokuje zapis z logiki — wyjście
  należy do tego, kto je wymusił, tak samo jak przy komendzie ręcznej.
- **Komenda ręczna do wyjścia, które prowadzi działający program, jest
  odrzucana** (`validate_command`). Inaczej operator i skan ścigałyby
  się o tę samą cewkę — komenda „nie działa" kilka milisekund później,
  co jest groźniejsze niż odmowa z wyjaśnieniem. Reguła obowiązuje tylko
  gdy skan naprawdę działa: zatrzymany program niczego nie prowadzi.
- **Fail-safe:** program skonfigurowany, ale niedziałający, dalej blokuje
  komendy („Logic Runtime Unavailable"). Zatrzymanie skanu sprowadza
  każde wyjście, którego program kiedykolwiek dotknął, do stanu
  bezpiecznego (cyfrowe `False`, analogowe `0.0`) — nie zostawia go
  zatrzaśniętego na ostatniej wartości.
- Zapis AO z logiki i z panelu przechodzą przez jedną funkcję
  (`EPWCore._route_analog_output()`), więc skalowanie jest to samo.
  Różnica jest zamierzona: zapis operatora ma bramkę Engineer i wpis do
  dziennika, zapis z logiki nie — program piszący swoje wyjście co cykl
  zalałby dziennik.

## 5. Sygnały systemowe — co jest podpięte

**`SYS.*`** — do prawdziwego stanu sterownika (`SystemSignalSource`):
`SYS.READY`, `SYS.HEALTH`, `SYS.FAULT`, `SYS.SCAN_TIME`,
`SYS.CYCLE_COUNT`, `SYS.SCAN_OVERRUN`, `SYS.FIRST_SCAN`,
`SYS.TRAINING_MODE`, `SYS.COMMS_OK`, `SYS.TIME_SYNC_OK`,
`SYS.ACCESS_LEVEL`, `SYS.ACCESS_USER/OPERATOR/ENGINEER` oraz generatory
`SYS.PULSE_*`/`SYS.BLINK_*` (z tej samej wspólnej tablicy okresów, co
symulacja w Studio — `shared/logic/engine/io_provider.py`).

**`SSWIN.*`** — do alarmówki (`runtime/epw_os/core/sswin_signals.py`).
Katalog opisuje **jedną centralę**, a runtime ma model **strefowy**, więc
tłumaczenie jest decyzją i stoi w jednym miejscu:

- `SSWIN.ARMED` = **wszystkie** strefy uzbrojone (i jest co najmniej jedna);
  `ARMED_PARTIAL` = część uzbrojona, część nie. Celowo ostrzej niż
  `IntrusionManager.get_system_state()`, które dla wskaźnika stanu uznaje
  „choć jedna strefa czuwa" za uzbrojenie — dla logiki to za mało: schemat
  pracujący „gdy obiekt uzbrojony" nie może widzieć ARMED, gdy pół obiektu
  jest otwarte.
- Stany „którakolwiek strefa" (`EXIT_DELAY`, `ENTRY_DELAY`, `ALARM_ACTIVE`,
  `TAMPER`, `FAULT`) — jedna strefa w alarmie **jest** alarmem systemu.
- `ALARM_LATCHED` to zatrzask, który przeżył przyczynę (pamięć alarmu
  aktywna, a strefa już nie w ALARM); `ALARM_MEMORY` — pamięć od ostatniego
  kasowania, także w trakcie alarmu.
- `DELAY_REMAINING` — najdłuższe trwające odliczanie; `ACTIVE_COUNT` —
  liczba naruszonych linii; `LAST_TRIGGER` — numer linii z pamięci alarmu.
- `READY_TO_ARM` — żadna linia naruszona ani w awarii. Linia wykluczona
  (bypass) **nadal** blokuje gotowość: wykluczenie służy do uzbrojenia
  mimo wszystko, nie jest powodem, by nazwać system gotowym.
- **Komendy** (`CMD_ARM`, `CMD_DISARM`, `CMD_RESET`) działają na
  **wszystkie strefy** — komenda z katalogu nie ma strefy do wskazania.
  Wykonują się **na zboczu narastającym** (blok trzymający sygnał w
  jedynce nie powtarza komendy co skan) i dopiero po sprawdzeniu poziomu
  dostępu, który deklaruje sam blok („Minimalny poziom dostępu" —
  Logic Studio to tylko zapisuje, egzekucja jest po stronie EPW-OS).

**Sygnalizator — to jest stan, nie wyjście.** Polecenie właściciela:
„chcę móc to swobodnie programować ustawiając bit wewnętrzny alarm i
pobudzenie danego DO który wyjdzie na syrenę". EPW-OS **nie steruje żadną
syreną**. Wystawia fakty, a schemat decyduje, co z nimi zrobić:

| Sygnał | Znaczy |
|---|---|
| `SSWIN.SIREN_ACTIVE` | sygnalizator ma teraz dźwięczeć — **to** podpina się do DO |
| `SSWIN.SIREN_TIME_LEFT` | ile sekund jeszcze wolno (0 = nie dźwięczy albo nie ma limitu) |
| `SSWIN.STROBE_ACTIVE` | pamięć alarmu — światło, które przeżywa dźwięk, aż ktoś skasuje alarm |
| `SSWIN.PANIC` | zadziałała linia napadowa i nikt tego jeszcze nie potwierdził |
| `SSWIN.CMD_SILENCE` | wycisz **sam dźwięk**: strefa zostaje w ALARM, pamięć i lampa zostają |

`SIREN_ACTIVE` gaśnie samo po czasie z nastawy `Sounder.siren_seconds`
(0 = bez ograniczenia), podczas gdy `ALARM_ACTIVE` i `STROBE_ACTIVE` trwają
dalej — syrena bez końca jest zwykle niezgodna z przepisami, a lampa i tak
pokazuje, że coś się stało. `CMD_SILENCE` jako jedyna komenda działa
**na system, nie na każdą strefę po kolei**: stan sygnalizatora jest jeden.

**Linia napadowa** (`LineType.PANIC`) alarmuje w **każdym** stanie strefy,
jak linia całodobowa, i nie podlega filtrowi dozoru nocnego. Różni się tym,
że domyślnie **nie uruchamia syreny** (`Sounder.panic_silent`) — sens
przycisku napadowego polega na tym, że stojący nad tobą człowiek nie
dowiaduje się, że go nacisnąłeś.

`UNSERVED_SIGNALS` jest dziś **puste**. Mechanizm został: odczyt sygnału,
na który ten sterownik nie odpowiada, daje wartość bezpieczną, a **zapis**
takiej komendy jest raz zgłaszany do logu — nie znika po cichu.

**Sygnały retencyjne (`MR.`/`MWR.`) przeżywają restart.** Ich wartości
leżą w `runtime_state.json` (sekcja `logic_retentive`), zapisywane co 30 s
i przy zatrzymaniu skanu — nie co skan: to stan, który ma przetrwać
restart, a nie zapis do rejestracji, i karta SD w sterowniku nie jest od
pisania z częstotliwością skanu. Przy starcie wracają **tylko** te
identyfikatory, które program faktycznie deklaruje jako retencyjne —
wartość po programie, który już ich nie zna, nie jest wskrzeszana.

### Do zrobienia (zgłoszone, nie zrobione w tym zadaniu)

- **`cycle_delayed_reads`** (diagnostyka „odczyt wyprzedza zapis")
  zostaje po stronie edytora — eksport tego nie niesie, a silnik tego
  nie czyta.
- ~~Sygnalizator alarmówki~~ — ZROBIONY 2026-09-20, jako **stan**:
  `SSWIN.SIREN_ACTIVE` / `SIREN_TIME_LEFT` / `STROBE_ACTIVE` / `CMD_SILENCE`,
  nastawy w `Sounder` (Studio → Strefy). Wyjście na syrenę rysuje inżynier.
- ~~Linia napadowa~~ — ZROBIONA 2026-09-20 (`LineType.PANIC`, `SSWIN.PANIC`).
- ~~Dozór częściowy (nocny)~~ — ZROBIONY 2026-09-20 (`ArmMode.NIGHT`,
  flaga `active_at_night` przy linii; `SSWIN.CMD_ARM_PARTIAL` działa).

## 6. Gdzie to jest w kodzie

| Plik | Rola |
|---|---|
| `shared/logic/program_loader.py` | eksport → `CompiledProgram` |
| `runtime/epw_os/core/logic_runtime.py` | `TagIOProvider`, `SystemSignalSource` |
| `runtime/epw_os/core/sswin_signals.py` | `SSWIN.*` — centrala vs strefy, komendy |
| `runtime/epw_os/core/logic_engine.py` | ładowanie, wątek skanu, fail-safe, blokada komend |
| `runtime/epw_os/core/epw_core.py` | złożenie tego w start/stop i stan zdrowia |
| `shared/tests/test_logic_execution_contract.py` | dowód równoważności Studio ↔ sterownik |
| `runtime/epw_os/tests/test_logic_execution.py` | zachowanie sterownika (skan, granice, odmowy) |
| `runtime/epw_os/tests/test_logic_visibility.py` | wskaźnik pracy, REST, przeładowanie bez restartu |
| `runtime/epw_os/tests/test_sswin_and_retentive.py` | mapowanie `SSWIN.*`, komendy, bity retencyjne |
| `runtime/epw_os/tests/test_intrusion_sounder_and_panic.py` | sygnalizator jako stan, linia napadowa |
