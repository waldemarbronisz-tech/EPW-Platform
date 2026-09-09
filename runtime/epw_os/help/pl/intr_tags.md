# Sygnały dla logiki (tagi Security.*)

System alarmowy nigdy sam nie steruje syreną, światłem ani niczego nie
wysyła — publikuje tylko stan jako zwykłe tagi, żeby program logiki mógł
reagować dowolnie, zależnie od potrzeb instalacji. Wszystkie zaczynają
się od `Security.`:

**Per strefa** (`<id>` to wewnętrzny identyfikator strefy, np. `Z1` —
widoczny obok jej nazwy w oknie Konfiguruj strefy):
- `Security.Zone.<id>.State` — DISARMED / EXIT_DELAY / ARMED /
  ENTRY_DELAY / ALARM
- `Security.Zone.<id>.ArmRequest` — **zapis** True uzbraja, False
  rozbraja tę strefę z poziomu logiki (kluczyk, pilot albo cokolwiek
  innego, co potrafi zapisać tag)
- `Security.Zone.<id>.CountdownRemaining` — sekundy pozostałe w
  odliczaniu wyjścia/wejścia, poza tym 0
- `Security.Zone.<id>.AlarmMemoryActive` — True, gdy w tej strefie
  wystąpił alarm od ostatniego jawnego skasowania — patrz
  [Pierwsza przyczyna i pamięć alarmu](help://intr_alarm_memory)
- `Security.Zone.<id>.AlarmMemoryFirstCauseLine` — identyfikator linii,
  która jako pierwsza wywołała aktualnie zapamiętany alarm, puste gdy
  AlarmMemoryActive jest False
- `Security.Zone.<id>.WalkTestActive` — True, gdy dla tej strefy trwa
  [tryb chodzenia](help://intr_walk_test)

**Per linia dozorowa** (`<id>` np. `L1`):
- `Security.Line.<id>.Violated` — bieżący stan naruszenia tej linii (po
  filtrowaniu minimalnym czasem naruszenia, jeśli skonfigurowane —
  patrz [Filtrowanie fałszywych alarmów](help://intr_filters))
- `Security.Line.<id>.MultiplicityCounting` — True, gdy trwa liczenie
  naruszeń, w oczekiwaniu na kolejne albo na upływ okna
- `Security.Line.<id>.Locked` — True, gdy ta linia jest automatycznie
  zablokowana po powtarzających się alarmach w tym cyklu uzbrojenia
- `Security.Line.<id>.State` — pełny stan tej linii: Secure / Violated
  / Tamper / Short / FaultOpen / Undetermined (linia w trybie stykowym
  przyjmuje tylko Secure albo Violated — patrz
  [Tryby linii](help://intr_input_modes))
- `Security.Line.<id>.Fault` — True, gdy linia jest w dowolnym stanie
  awarii (Tamper / Short / FaultOpen / Undetermined)
- `Security.Line.<id>.Suspect` — True, gdy linia przekroczyła swój
  skonfigurowany maksymalny czas bez naruszenia — patrz
  [Życie linii i wykrywanie ciszy](help://intr_line_life)

**Zbiorczo (system):**
- `Security.System.State` — te same 5 wartości, zagregowane po
  wszystkich strefach (jedna strefa w ALARM sprawia, że to też ALARM,
  i tak dalej w dół ważności)
- `Security.System.Alarm` — True, gdy jakakolwiek strefa jest w ALARM
- `Security.System.EntryCountdownActive` / `.ExitCountdownActive` —
  True, gdy jakakolwiek strefa odlicza dany czas (do sygnalizacji
  dźwiękowej)
- `Security.Supervisory.Violated` — True, gdy jakakolwiek linia typu
  Dozorowa jest naruszona (dla logiki sterującej np. oświetleniem, bez
  czynienia tych czujek częścią alarmu)
- `Security.System.LineFault` — True, gdy jakakolwiek linia dozorowa
  jest w stanie awarii
- `Security.Power.MainsOk` / `Security.Power.BatteryOk` — dwa
  niezależne, opcjonalne sprawdzenia zasilania. **True oznacza stan
  sprawny** (konwencja obowiązująca w całej platformie: sygnał
  sprawności jest wysoki, więc urwany kabel albo martwy moduł daje
  stan niski i wygląda jak awaria, a nie jak stan normalny) — False
  tylko wtedy, gdy dane wejście jest faktycznie skonfigurowane I
  odczytuje stan niesprawny; brak konfiguracji odczytuje jako True
  (nic do zgłoszenia, tak jakby to sprawdzenie nie istniało) — patrz
  [Nadzór zasilania](help://intr_power_supervision)
- `Security.System.TechnicalAlarm` — True, gdy którekolwiek z powyższych
  sprawdzeń zasilania NIE JEST sprawne (`MainsOk` albo `BatteryOk` ma
  wartość False); osobna kategoria od `Security.System.Alarm`, który
  pozostaje ściśle o włamaniu

Zapis `Security.Zone.<id>.ArmRequest` to jedyny tag, który ten system
odczytuje jako wejście — każdy pozostały powyżej jest tylko do odczytu,
zapisywany przez sam system.
