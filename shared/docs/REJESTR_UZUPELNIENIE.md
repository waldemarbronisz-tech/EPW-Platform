# Rejestr sygnałów — materiał uzupełniający (Task B4)

Pełny inwentarz każdego tagu rejestrowanego w `TagManager` w tym
programie, na podstawie przeglądu KAŻDEGO wywołania `add_tag()` w
`epw_os/core/*.py` (jedyne miejsca, które kiedykolwiek rejestrują tag) —
nie tylko żywego zrzutu z jednego uruchomienia, które nie pokazałoby
tagów dynamicznych bez wcześniej skonfigurowanych stref/linii/urządzeń.
Zweryfikowane też przez rzeczywisty eksport (`build_tag_list_export()`)
z instancji `EPWCore` ze skonfigurowaną przykładową strefą, linią,
zabezpieczeniem procesowym i urządzeniami ELA/ADA/EPM.

Ten plik jest gotowy do przeniesienia do zewnętrznego rejestru sygnałów
w arkuszu — jedna tabela, jeden wiersz na tag albo na wzorzec tagów
dynamicznych (per strefa/linia/urządzenie/punkt), ze wzorcem zamiast
konkretnych instancji, zgodnie z wymogiem zadania.

Skróty w kolumnie **kto czyta**: *Logika* = program logiki (przez
LogicEngine, każdy tag jest w zasadzie czytelny), *API* = REST API
(`GET /api/v1/tags`), *MQTT* = integracja MQTT (Część A tego zadania —
publikuje WSZYSTKIE tagi generycznie), *Eksport* = eksport listy
sygnałów (`tag_export.py`) i Historian (`tag_changed` → baza danych,
z zastrzeżeniem strefy nieczułości) — te cztery czytają dosłownie
każdy tag w systemie, więc w wierszach poniżej wymienieni są tylko
czytelnicy DODATKOWI, specyficzni dla danego tagu/grupy.

| nazwa | typ | grupa | moduł-właściciel | co znaczy | kiedy TRUE | kto czyta (dodatkowo) | uwaga implementacyjna |
|---|---|---|---|---|---|---|---|
| `DI1`..`DI64` (wzorzec) | BOOL | DI | Digital Inputs (`tag_manager.py`) | Stan fizycznego wejścia cyfrowego kanału N | Styk zamknięty na tym kanale | Strona Digital Inputs, System Alarmowy (linie dozorowe mogą być podpięte pod dowolny DI), Control Outputs (DO01-DO04 czytają DI1-DI4 jako swój feedback) | Rejestrowane zawsze (tylko gdy projekt NIE definiuje własnych urządzeń — w przeciwnym razie zamiast tego rejestrowane są `<id>.DIxx` per urządzenie, patrz niżej) |
| `DO05`..`DO64` (wzorzec) | BOOL | DO | Digital Outputs (`tag_manager.py`) | Stan/rozkaz wyjścia cyfrowego kanału N — sam sobie jest też własnym sprzężeniem zwrotnym | Wyjście zamknięte/wysterowane | Strona Control Outputs, CommandManager (rozkaz `DOxx.CLOSE`/`.OPEN`) | DO01-DO04 NIE mają własnego tagu — ich stan czyta się z DI1-DI4 (patrz wyżej); routing komend dla nich nadal używa identyfikatora `DO01`..`DO04`, ale to nazwa polecenia, nie nazwa tagu |
| `AI1`..`AI16` / dowolna nazwa (wzorzec, punkty analogowe) | REAL | AI | Analog Inputs (`epw_core.py`, `project_manager.py`) | Wartość inżynierska skonfigurowanego punktu analogowego | n/d (REAL) | Strona Analog Inputs, Zabezpieczenia Procesowe (`Process.<id>.Exceeded` czyta wskazany punkt), Trendy | Kolekcja DYNAMICZNA (dodawana/usuwana w czasie działania, nie stały zestaw jak DI/DO) — nazwa, opis, skalowanie i jednostka w pełni operatorskie, persystowane w `project.json`'s `analog_points` |
| `Cabinet.SystemHealth` | STRING | Cabinet | Cabinet Monitoring (`tag_manager.py`) | Zbiorczy stan zdrowia szafy pokazywany na Widoku głównym | n/d (STRING: np. "HEALTHY") | Widok główny | Żaden fizyczny czujnik dziś tego nie zapisuje — trzyma domyślną wartość, zaślepka pod przyszły agregat |
| `Cabinet.TempInside` | REAL | Cabinet | Cabinet Monitoring (`tag_manager.py`) | Temperatura wewnątrz szafy (°C) | n/d (REAL) | Widok główny | Żaden fizyczny czujnik dziś tego nie zapisuje (statyczna/symulowana wartość domyślna) |
| `Cabinet.TempOutside` | REAL | Cabinet | Cabinet Monitoring (`tag_manager.py`) | Temperatura otoczenia na zewnątrz szafy (°C) | n/d (REAL) | Widok główny | Jak wyżej — brak realnego czujnika |
| `Cabinet.Humidity` | REAL | Cabinet | Cabinet Monitoring (`tag_manager.py`) | Wilgotność względna wewnątrz szafy (%) | n/d (REAL) | Widok główny | Jak wyżej — brak realnego czujnika |
| `Cabinet.Door` | STRING | Cabinet | Cabinet Monitoring (`tag_manager.py`) | Stan styku drzwi szafy | n/d (STRING: OPEN/CLOSED) | Widok główny, Liczniki łączeń (test) | Jak wyżej — brak realnego czujnika |
| `Cabinet.Heater` | STRING | Cabinet | Cabinet Monitoring (`tag_manager.py`) | Stan grzałki antykondensacyjnej szafy | n/d (STRING: ON/OFF) | Widok główny | Jak wyżej — brak realnego wyjścia sterującego |
| `Cabinet.Fan` | STRING | Cabinet | Cabinet Monitoring (`tag_manager.py`) | Stan wentylatora chłodzącego szafy | n/d (STRING) | Widok główny | Jak wyżej — brak realnego wyjścia sterującego |
| `Cabinet.Alarm` | STRING | Cabinet | Cabinet Monitoring (`tag_manager.py`) | Zbiorczy alarm szafy (np. otwarte drzwi, przegrzanie) | n/d (STRING: "NONE" gdy brak) | Widok główny | Jak wyżej — brak realnego czujnika |
| `Cabinet.Fault` | STRING | Cabinet | Cabinet Monitoring (`tag_manager.py`) | Zbiorcza awaria szafy | n/d (STRING: "NONE" gdy brak) | Widok główny | Jak wyżej — brak realnego czujnika |
| `Device.OrangePi.Status` / `Device.ELA01.Status` / `Device.ADA01.Status` / `Device.Modbus.Status` (albo `Device.<id>.Status` dla urządzeń projektowych — wzorzec) | STRING | Device | Device Communication Status (`tag_manager.py`, aktualizowane przez `epw_core.py`/`device_manager.py`) | Status łączności z danym urządzeniem | n/d (STRING: ONLINE/OFFLINE/COMM_FAILURE) | Widok główny, pasek statusu ("COMM: OK"/"COMM: N OFFLINE") | Startuje jako OFFLINE (nie optymistycznie ONLINE) — przechodzi w ONLINE dopiero po realnym heartbeat komunikacyjnym; COMM_FAILURE dodatkowo podnosi alarm `DEVICE_COMM_<id>` |
| `EMERGENCY_STOP` | BOOL | EMERGENCY_STOP | System / Core (`tag_manager.py`) | Stan obwodu ZATRZYMANIA AWARYJNEGO | Obwód E-STOP zadziałał | AlarmManager (podnosi/kasuje alarm priorytetu 4), SafetyKernel/interlock (czyta, nigdy nie zapisuje) | Nic w tym symulowanym środowisku dziś tego nie zapisuje, ale jest to realnie bezpieczeństwo-istotny sygnał, jeśli coś zacznie |
| `System.Theme` | INT | System | System / Core (`epw_core.py`, `themes.py`) | Numer aktywnego motywu wizualnego (0=Industrial…4=SimCity 2000) | n/d (INT) | GUI (`ThemeManager`) | JEDYNY tag dziś jawnie zapisywalny z logiki (patrz `tools_export_tag_list`); zapis z logiki ma pierwszeństwo nad trybem automatycznym dzień/noc, dopóki tryb pracy nie zostanie ręcznie zmieniony w Ustawieniach |
| `System.Mode` | STRING | System | System / Core (`tag_manager.py`) | Miał odzwierciedlać `SIMULATION MODE`/`LIVE MODE` | n/d (STRING) | — | **ZNALEZISKO PRZY AUDYCIE (poza zakresem tego zadania — nie naprawiano):** tag NIGDY nie jest rejestrowany przez `add_tag()`, a `TagManager.set_mode()` mimo to woła `update_tag("System.Mode", ...)`, co rzuca `ValueError: Unknown tag` przy każdej zmianie trybu — połykane po cichu przez `EventBus.emit()`'s własny `try/except`. Sam tryb (`tag_manager.mode`) mimo to zmienia się poprawnie; tylko ten tag nigdy realnie nie istnieje. Zgłoszone jako osobna usterka do naprawy w przyszłym zadaniu, zgodnie z GRANICE tego zadania ("nie zmieniaj trybów") |
| `Sim.Voltage` | REAL | Sim | Simulation Sandbox (`tag_manager.py`) | Suwak amplitudy napięcia na stronie Power Quality | n/d (REAL) | Strona Power Quality | `quality=SIMULATED` — jawnie oznaczone jako brak realnego sygnału |
| `Sim.Frequency` | REAL | Sim | Simulation Sandbox (`tag_manager.py`) | Suwak częstotliwości na stronie Power Quality | n/d (REAL) | Strona Power Quality | `quality=SIMULATED` |
| `Meas.L1` / `Meas.L2` / `Meas.L3` | REAL | Meas | Simulated Measurements (`tag_manager.py`, zapisywane przez `page_entry_gate.py`) | Symulowane napięcie szyny, faza 1/2/3 | n/d (REAL) | Widok główny (`recalculate_electricity()`) | `quality=SIMULATED` — brak fizycznego licznika mocy |
| `Meas.I1` | REAL | Meas | Simulated Measurements (`tag_manager.py`) | Symulowany prąd zasilacza I1 | n/d (REAL) | Weryfikacja Trybu inżyniera (scenariusz nadprądowy) | `quality=SIMULATED` — brak fizycznego przekładnika prądowego |
| `<dev_id>.DI<NN>` (wzorzec, urządzenia typu ELA z `project.json`'s `devices`) | BOOL | `<dev_id>` | Multi-device hardware I/O (`tag_manager.configure()`) | Wejście cyfrowe kanału N na module ELA `<dev_id>` | Styk zamknięty | Jak DI1..DI64 powyżej | `quality=NOT_INITIALIZED` do pierwszego realnego odczytu sterownika; używane TYLKO gdy `project.json` definiuje własne `devices` (inaczej rejestrowany jest płaski DI1..DI64) |
| `<dev_id>.DO<NN>` (wzorzec, ADA) | BOOL | `<dev_id>` | Multi-device hardware I/O (`tag_manager.configure()`) | Wyjście cyfrowe kanału N na module ADA `<dev_id>` | Wyjście zamknięte/wysterowane | Jak DO powyżej | `quality=NOT_INITIALIZED` do pierwszego realnego odczytu sterownika |
| `<dev_id>.UL1.RMS` / `.UL2.RMS` / `.UL3.RMS` (wzorzec, EPM) | REAL | `<dev_id>` | Multi-device hardware I/O (`tag_manager.configure()`) | Napięcie fazowe RMS, faza 1/2/3, z licznika mocy `<dev_id>` (V) | n/d (REAL) | — | `quality=NOT_INITIALIZED` do pierwszego realnego odczytu |
| `<dev_id>.FREQ` (wzorzec, EPM) | REAL | `<dev_id>` | Multi-device hardware I/O (`tag_manager.configure()`) | Częstotliwość sieci mierzona przez licznik `<dev_id>` (Hz) | n/d (REAL) | — | `quality=NOT_INITIALIZED` do pierwszego realnego odczytu |
| `Safety.<device_id>.Healthy` / `.Fault` (wzorzec, per zarejestrowane urządzenie) | BOOL | Safety | Safety Kernel (`safety_kernel.py`) | Czy dane urządzenie odpowiada na kontrole zdrowia SafetyKernel / zatrzask awarii tego urządzenia | Healthy: urządzenie odpowiada; Fault: zatrzask, kasowany tylko przez jawne potwierdzenie | Strona Alarmy (potwierdzanie), Widok główny | `.Fault` to ZATRZASK — nie czyści się sam nawet po powrocie zdrowia, wymaga potwierdzenia na stronie Alarmy |
| `Safety.System.Healthy` / `.Fault` | BOOL | Safety | Safety Kernel (`safety_kernel.py`) | Zbiorczy stan zdrowia po wszystkich monitorowanych urządzeniach | Jak wyżej, zagregowane | Jak wyżej | Jak wyżej — zatrzask |
| `Security.Zone.<id>.State` (wzorzec, per strefa) | STRING | Security | Intrusion Alarm System (`intrusion_manager.py`) | Bieżący stan cyklu życia strefy | n/d (STRING: DISARMED/EXIT_DELAY/ARMED/ENTRY_DELAY/ALARM) | Podgląd systemu alarmowego, pasek statusu | — |
| `Security.Zone.<id>.ArmRequest` (wzorzec) | BOOL | Security | Intrusion Alarm System (`intrusion_manager.py`) | **Zapisywalny** rozkaz uzbrojenia/rozbrojenia z logiki | Zapis True uzbraja, False rozbraja | Logika (jedyny INPUT tego modułu) | Obserwowana jest ZMIANA POZIOMU (nie tylko zbocze True), więc kluczyk (stan trzymany) działa tak samo jak przycisk chwilowy |
| `Security.Zone.<id>.CountdownRemaining` (wzorzec) | INT | Security | Intrusion Alarm System (`intrusion_manager.py`) | Sekundy pozostałe w odliczaniu wyjścia/wejścia tej strefy | n/d (INT, 0 poza odliczaniem) | Podgląd | — |
| `Security.Zone.<id>.AlarmMemoryActive` (wzorzec) | BOOL | Security | Intrusion Alarm System (`intrusion_manager.py`) | Czy w tej strefie wystąpił alarm od ostatniego jawnego skasowania | Alarm zapamiętany, nieskasowany | Podgląd (dialog pamięci alarmu) | Przeżywa restart programu — persystowane w `project.json` |
| `Security.Zone.<id>.AlarmMemoryFirstCauseLine` (wzorzec) | STRING | Security | Intrusion Alarm System (`intrusion_manager.py`) | Id linii, która jako pierwsza wywołała zapamiętany alarm | n/d (STRING, puste gdy AlarmMemoryActive=False) | Podgląd | — |
| `Security.Zone.<id>.WalkTestActive` (wzorzec) | BOOL | Security | Intrusion Alarm System (`intrusion_manager.py`) | Czy dla tej strefy trwa tryb chodzenia | Tryb chodzenia aktywny | Podgląd | W tym trybie naruszenia są rejestrowane, ale NIGDY nie alarmują |
| `Security.Line.<id>.Violated` (wzorzec, per linia) | BOOL | Security | Intrusion Alarm System (`intrusion_manager.py`) | Bieżący stan naruszenia linii (po filtrowaniu) | Linia naruszona | Podgląd, Konfiguracja | — |
| `Security.Line.<id>.Locked` (wzorzec) | BOOL | Security | Intrusion Alarm System (`intrusion_manager.py`) | Czy linia auto-zablokowana po powtarzających się alarmach | Zablokowana do rozbrojenia strefy | Podgląd | — |
| `Security.Line.<id>.MultiplicityCounting` (wzorzec) | BOOL | Security | Intrusion Alarm System (`intrusion_manager.py`) | Czy trwa liczenie naruszeń w oknie wielokrotności | Liczenie w toku | Podgląd | — |
| `Security.Line.<id>.State` (wzorzec) | STRING | Security | Intrusion Alarm System (`intrusion_manager.py`) | Pełny sklasyfikowany stan linii | n/d (STRING: Secure/Violated/Tamper/Short/FaultOpen/Undetermined) | Podgląd, Konfiguracja | Tryb stykowy przyjmuje tylko Secure/Violated |
| `Security.Line.<id>.Fault` (wzorzec) | BOOL | Security | Intrusion Alarm System (`intrusion_manager.py`) | Czy linia jest w dowolnym stanie awarii | Tamper/Short/FaultOpen/Undetermined | Podgląd | Alarmuje ZAWSZE, niezależnie od stanu uzbrojenia |
| `Security.Line.<id>.Suspect` (wzorzec) | BOOL | Security | Intrusion Alarm System (`intrusion_manager.py`) | Czy linia przekroczyła maksymalny czas ciszy | Brak naruszenia dłużej niż próg | Podgląd | Tylko OSTRZEŻENIE, nigdy alarm |
| `Security.System.State` | STRING | Security | Intrusion Alarm System (`intrusion_manager.py`) | Zbiorczy stan po wszystkich strefach | n/d (STRING, jak Zone.State) | Pasek statusu | Jedna strefa w ALARM czyni to też ALARM |
| `Security.System.Alarm` | BOOL | Security | Intrusion Alarm System (`intrusion_manager.py`) | Czy jakakolwiek strefa jest w ALARM | Dowolna strefa w ALARM | Pasek statusu | — |
| `Security.System.EntryCountdownActive` / `.ExitCountdownActive` | BOOL | Security | Intrusion Alarm System (`intrusion_manager.py`) | Czy jakakolwiek strefa odlicza dany czas | Trwa odliczanie | Logika (sygnalizacja dźwiękowa) | — |
| `Security.Supervisory.Violated` | BOOL | Security | Intrusion Alarm System (`intrusion_manager.py`) | Czy jakakolwiek linia typu Dozorowa jest naruszona | Naruszenie dozorowe | Logika (np. oświetlenie) | Nie czyni czujki częścią alarmu |
| `Security.System.LineFault` | BOOL | Security | Intrusion Alarm System (`intrusion_manager.py`) | Czy jakakolwiek linia jest w stanie awarii | Dowolna linia w awarii | Pasek statusu | — |
| `Security.Power.MainsOk` | BOOL | Security | Intrusion Alarm System (`intrusion_manager.py`) | Nadzór zasilania sieciowego (opcjonalny) | **True = sprawny** (konwencja całej platformy) | Logika, dziennik audytowy | Fix `fix/power-supervision-polarity`: przed tą zmianą był to `MainsFailed` (True=awaria) — patrz `intr_tags.md` |
| `Security.Power.BatteryOk` | BOOL | Security | Intrusion Alarm System (`intrusion_manager.py`) | Nadzór akumulatora (opcjonalny) | **True = sprawny** | Logika, dziennik audytowy | Jak wyżej |
| `Security.System.TechnicalAlarm` | BOOL | Security | Intrusion Alarm System (`intrusion_manager.py`) | Alarm techniczny — osobna kategoria od włamaniowego | MainsOk LUB BatteryOk = False | Logika, dziennik audytowy | Żadna strona GUI dziś tego nie wyświetla wprost (znalezisko audytu pomocy — poprawiono `intr_power_supervision.md`, nie kod) |
| `Process.<id>.Exceeded` (wzorzec, per zabezpieczenie procesowe) | BOOL | Process | Process Protections (`process_protection_manager.py`) | Czy powiązany punkt analogowy jest poza skonfigurowanym pasmem (po histerezie/opóźnieniu) | Poza pasmem, po opóźnieniu | Logika | Zawsze False, gdy zabezpieczenie jest wyłączone (`enabled=False`), niezależnie od żywej wartości |
| dowolna nazwa istniejącego `output_tag`/`feedback_tag` z definicji scenariusza (wzorzec, Tryb prezentacji) | BOOL | (nazwa tagu) | Presentation Mode (`presentation_mode.py`) | Tag-zaślepka tworzony na żądanie, gdy scenariusz demonstracyjny odwołuje się do nazwy, która jeszcze nie istnieje | n/d | — | `quality=SIMULATED`, `source="PRESENTATION"`; tag, który już istnieje jako prawdziwy, NIGDY nie jest tym nadpisywany |
| `Link.<identyfikator>.In<nazwa>` (wzorzec, Część A5 tego zadania) | BOOL/REAL/INT/DINT/STRING (konfigurowalny) | Link | MQTT integration (`mqtt_manager.py`, NOWY w tym zadaniu) | Dana informacyjna z innego sterownika, zmapowana z jego tematu MQTT | Zależy od typu — surowa wartość ostatniej otrzymanej wiadomości | Logika (jedyny odbiorca — dane tylko do odczytu) | `timeout=stale_after_s` z konfiguracji mapowania — oznaczany `STALE` przez ten sam, już istniejący, generyczny mechanizm `TagManager.check_watchdogs()`, nie nowy, osobny zegar; zapis tego tagu NIGDY nie wywołuje żadnego działania w programie |

## Uwagi ogólne do rejestru

- **Kolumna "kiedy TRUE"** nie ma zastosowania (`n/d`) dla tagów typu
  STRING/INT/REAL — te opisano w kolumnie "co znaczy" zamiast.
- **`quality`** to osobny, dodatkowy wymiar każdego tagu (GOOD / BAD /
  UNCERTAIN / STALE / COMM_FAILURE / SIMULATED / NOT_INITIALIZED),
  niezależny od jego wartości — pominięty jako osobna kolumna, ale
  odnotowany w "uwaga implementacyjna" wszędzie, gdzie jest inny niż
  domyślny GOOD.
- **Kompletność:** każde wystąpienie `.add_tag(` w `epw_os/core/*.py`
  (jedyne miejsce, gdzie tagi kiedykolwiek powstają — potwierdzone
  wyszukiwaniem `grep -rn "\.add_tag(" epw_os/`) jest reprezentowane
  powyżej, albo jako konkretny tag, albo jako jeden wiersz-wzorzec dla
  całej rodziny tagów dynamicznych.
- **`System.Mode`** to jedyne PRAWDZIWE znalezisko usterki (nie tylko
  dokumentacyjne) z tego przeglądu — zgłoszone tutaj i NIE naprawione,
  zgodnie z GRANICE tego zadania ("nie zmieniaj trybów pracy").
