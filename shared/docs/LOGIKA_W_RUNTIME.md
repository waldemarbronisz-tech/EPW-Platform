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
   programu.

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

## 5. Sygnały systemowe — co jest podpięte, a co nie

Podpięte do prawdziwego stanu sterownika (`SystemSignalSource`):
`SYS.READY`, `SYS.HEALTH`, `SYS.FAULT`, `SYS.SCAN_TIME`,
`SYS.CYCLE_COUNT`, `SYS.SCAN_OVERRUN`, `SYS.FIRST_SCAN`,
`SYS.TRAINING_MODE`, `SYS.COMMS_OK`, `SYS.TIME_SYNC_OK`,
`SYS.ACCESS_LEVEL`, `SYS.ACCESS_USER/OPERATOR/ENGINEER` oraz generatory
`SYS.PULSE_*`/`SYS.BLINK_*` (z tej samej wspólnej tablicy okresów, co
symulacja w Studio — `shared/logic/engine/io_provider.py`).

### Do zrobienia (zgłoszone, nie zrobione w tym zadaniu)

- **`SSWIN.*` nie są podpięte.** Sygnały katalogu są systemowe
  (cała centrala), a model alarmówki w runtime jest **strefowy**
  (`IntrusionManager.arm_zone()`/`get_zone_state()`). Odwzorowanie
  wymaga decyzji, co znaczy „uzbrojona centrala" przy wielu strefach —
  to decyzja projektowa, nie przepisanie. Do czasu jej podjęcia odczyt
  daje wartość bezpieczną (`False`/`0.0`), a **zapis** (`SSWIN.CMD_*`
  z bloku `system.signal_out`) jest zgłaszany do logu raz na sygnał,
  żeby nie zniknął po cichu.
- **Sygnały wewnętrzne retencyjne (`MR.`/`MWR.`) nie przeżywają
  restartu.** Studio tylko przenosi flagę `retentive` (tak mówi jego
  własna dokumentacja), a trwałość jest zadaniem EPW OS — dziś ich
  wartości żyją w pamięci procesu, tak samo jak nieretencyjne.
- **`cycle_delayed_reads`** (diagnostyka „odczyt wyprzedza zapis")
  zostaje po stronie edytora — eksport tego nie niesie, a silnik tego
  nie czyta.
- **Wgranie nowego programu wymaga restartu sterownika** — tak samo jak
  reszta projektu (patrz `PROJEKT_EPW_ZADANIA.md`, p. 3).

## 6. Gdzie to jest w kodzie

| Plik | Rola |
|---|---|
| `shared/logic/program_loader.py` | eksport → `CompiledProgram` |
| `runtime/epw_os/core/logic_runtime.py` | `TagIOProvider`, `SystemSignalSource` |
| `runtime/epw_os/core/logic_engine.py` | ładowanie, wątek skanu, fail-safe, blokada komend |
| `runtime/epw_os/core/epw_core.py` | złożenie tego w start/stop i stan zdrowia |
| `shared/tests/test_logic_execution_contract.py` | dowód równoważności Studio ↔ sterownik |
| `runtime/epw_os/tests/test_logic_execution.py` | zachowanie sterownika (skan, granice, odmowy) |
