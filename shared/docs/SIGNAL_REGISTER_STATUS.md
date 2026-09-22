# Rejestr sygnałów — stan wdrożenia

**Plik generowany.** Nie edytuj go ręcznie — uruchom
`python shared/docs/generate_signal_register_status.py` z korzenia repo.
Źródłem jest `EPW_Rejestr_Bitow_Wewnetrznych_V2.xlsx` (arkusz
`01_REJESTR_BITOW`), porównywany z `shared/logic/system_signals_catalog.json`
(wersja katalogu **2.2.0**). Arkusz jest tylko czytany.

Pozycji w rejestrze: **200**.

| stan | pozycji |
|---|---:|
| w katalogu i obsłużony | 77 |
| do zrobienia | 72 |
| czeka na firmware | 24 |
| czeka na sprzęt | 21 |
| poza katalogiem | 4 |
| przyszłość | 2 |

## Co znaczy każdy stan

- **w katalogu i obsłużony** — sygnał jest w katalogu platformy, a sterownik
  realnie wylicza jego wartość. Logika może go użyć.
- **w katalogu, bez źródła** — nazwa ustalona, ale nic jeszcze nie liczy
  wartości. Panel Sygnały pokazuje to wprost jako „brak źródła”.
- **czeka na sprzęt** — potrzebny punkt z nadaną rolą w Studio (zasilanie, UPS).
- **czeka na firmware** — potrzebne rejestry diagnostyczne w firmware karty.
- **przyszłość** — koncepcja bez implementacji po żadnej stronie.
- **poza katalogiem** — sygnał należy do innej warstwy (markery użytkownika,
  adresy fizyczne), więc katalog platformy nie jest jego miejscem.
- **do zrobienia** — mieści się w katalogu, jeszcze go tam nie ma.

## Zmiany nazw

Decyzja właściciela (2026-09-21): prefiks alarmówki to `SEC.`, a komendy
stają się żądaniami `REQ.SEC.*`. To **nie** jest zamiana prefiksu —
szczegóły i powód w `shared/logic/signal_renames.py`.

### Nazwy wzięte z rejestru (12)

| było | jest |
|---|---|
| `SSWIN.ALARM_ACTIVE` | `SEC.SYSTEM.ALARM` |
| `SSWIN.ALARM_MEMORY` | `SEC.SYSTEM.ALARM_MEMORY` |
| `SSWIN.ARMED` | `SEC.SYSTEM.ARMED` |
| `SSWIN.CMD_ARM` | `REQ.SEC.ARM_ALL` |
| `SSWIN.CMD_DISARM` | `REQ.SEC.DISARM_ALL` |
| `SSWIN.CMD_RESET` | `REQ.SEC.CLEAR_ALARM_MEMORY` |
| `SSWIN.CMD_SILENCE` | `REQ.SEC.SILENCE` |
| `SSWIN.DISARMED` | `SEC.SYSTEM.DISARMED` |
| `SSWIN.ENTRY_DELAY` | `SEC.SYSTEM.ENTRY_DELAY` |
| `SSWIN.EXIT_DELAY` | `SEC.SYSTEM.EXIT_DELAY` |
| `SSWIN.FAULT` | `SEC.SYSTEM.FAULT` |
| `SSWIN.TAMPER` | `SEC.SYSTEM.TAMPER` |

### Nazwy ustalone tutaj, przyjęte (11)

Te sygnały **nie mają wiersza w rejestrze** — sterownik obsługuje je dziś,
a rejestr ich nie obejmuje (brak dozoru częściowego, sygnalizatora i linii
napadowej; rejestr jest też wyłącznie BOOL-owy). Nazwano je konsekwentnie
z gramatyką rejestru i **właściciel przyjął je 2026-09-21** — to nie jest
pozycja oczekująca. Wypisane osobno tylko po to, żeby przyszła wersja
rejestru wiedziała, które nazwy powstały tutaj.

| było | jest |
|---|---|
| `SSWIN.ACTIVE_COUNT` | `SEC.SYSTEM.ACTIVE_COUNT` |
| `SSWIN.ALARM_LATCHED` | `SEC.SYSTEM.ALARM_LATCHED` |
| `SSWIN.ARMED_PARTIAL` | `SEC.SYSTEM.ARMED_PARTIAL` |
| `SSWIN.CMD_ARM_PARTIAL` | `REQ.SEC.ARM_ALL_PARTIAL` |
| `SSWIN.DELAY_REMAINING` | `SEC.SYSTEM.DELAY_REMAINING` |
| `SSWIN.LAST_TRIGGER` | `SEC.SYSTEM.LAST_TRIGGER` |
| `SSWIN.PANIC` | `SEC.SYSTEM.PANIC` |
| `SSWIN.READY_TO_ARM` | `SEC.SYSTEM.READY_TO_ARM` |
| `SSWIN.SIREN_ACTIVE` | `SEC.SYSTEM.SIREN_ACTIVE` |
| `SSWIN.SIREN_TIME_LEFT` | `SEC.SYSTEM.SIREN_TIME_LEFT` |
| `SSWIN.STROBE_ACTIVE` | `SEC.SYSTEM.STROBE_ACTIVE` |

## Pozycje rejestru

| ID / wzorzec | grupa | kierunek | stan | uwaga |
|---|---|---|---|---|
| `SYS.READY` | SYS | SYSTEM INPUT | w katalogu i obsłużony |  |
| `SYS.RUNNING` | SYS | SYSTEM INPUT | w katalogu i obsłużony |  |
| `SYS.STARTING` | SYS | SYSTEM INPUT | w katalogu i obsłużony |  |
| `SYS.STOPPING` | SYS | SYSTEM INPUT | w katalogu i obsłużony |  |
| `SYS.DEGRADED` | SYS | SYSTEM INPUT | w katalogu i obsłużony |  |
| `SYS.FAIL` | SYS | SYSTEM INPUT | w katalogu i obsłużony |  |
| `SYS.CONFIG_OK` | SYS | SYSTEM INPUT | w katalogu i obsłużony |  |
| `SYS.CONFIG_FAULT` | SYS | SYSTEM INPUT | w katalogu i obsłużony |  |
| `SYS.TIME_SYNC_OK` | SYS | SYSTEM INPUT | w katalogu i obsłużony |  |
| `SYS.TIME_SYNC_FAULT` | SYS | SYSTEM INPUT | w katalogu i obsłużony |  |
| `SYS.FIRST_SCAN` | SYS | SYSTEM INPUT | w katalogu i obsłużony |  |
| `SYS.HEARTBEAT` | SYS | SYSTEM INPUT | w katalogu i obsłużony |  |
| `SYS.CLOCK_100MS` | SYS | SYSTEM INPUT | w katalogu i obsłużony |  |
| `SYS.CLOCK_1S` | SYS | SYSTEM INPUT | w katalogu i obsłużony |  |
| `SYS.CLOCK_10S` | SYS | SYSTEM INPUT | w katalogu i obsłużony |  |
| `SYS.CLOCK_1MIN` | SYS | SYSTEM INPUT | w katalogu i obsłużony |  |
| `RT.LOGIC.READY` | Logic Runtime | SYSTEM INPUT | w katalogu i obsłużony |  |
| `RT.LOGIC.RUNNING` | Logic Runtime | SYSTEM INPUT | w katalogu i obsłużony |  |
| `RT.LOGIC.FAIL` | Logic Runtime | SYSTEM INPUT | w katalogu i obsłużony |  |
| `RT.LOGIC.OVERRUN` | Logic Runtime | SYSTEM INPUT | w katalogu i obsłużony |  |
| `RT.LOGIC.PROJECT_OK` | Logic Runtime | SYSTEM INPUT | w katalogu i obsłużony |  |
| `RT.LOGIC.PROJECT_FAULT` | Logic Runtime | SYSTEM INPUT | w katalogu i obsłużony |  |
| `RT.SYNOPTIC.READY` | Synoptic Runtime | SYSTEM INPUT | w katalogu i obsłużony |  |
| `RT.SYNOPTIC.FAIL` | Synoptic Runtime | SYSTEM INPUT | w katalogu i obsłużony |  |
| `RT.SYNOPTIC.BINDING_FAULT` | Synoptic Runtime | SYSTEM INPUT | w katalogu i obsłużony |  |
| `COMM.ALL_OK` | COMM | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `COMM.ANY_DEVICE_OFFLINE` | COMM | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `COMM.ANY_DEVICE_FAULT` | COMM | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `COMM.BUS_FAULT` | COMM | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `COMM.RS485_FAULT` | COMM | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `COMM.ETHERNET_FAULT` | COMM | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `COMM.LINK_DEGRADED` | COMM | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `COMM.<device_id>.ONLINE` | COMM | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `COMM.<device_id>.OFFLINE` | COMM | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `COMM.<device_id>.FAULT` | COMM | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `COMM.<device_id>.TIMEOUT` | COMM | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `COMM.<device_id>.DEGRADED` | COMM | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `DEV.<device_id>.READY` | DEVICE HEALTH | SYSTEM INPUT | czeka na firmware | wymaga rejestrów diagnostycznych w firmware karty - mapa rejestrów ELA01 |
| `DEV.<device_id>.RUNNING` | DEVICE HEALTH | SYSTEM INPUT | czeka na firmware | wymaga rejestrów diagnostycznych w firmware karty - mapa rejestrów ELA01 |
| `DEV.<device_id>.FAULT` | DEVICE HEALTH | SYSTEM INPUT | czeka na firmware | wymaga rejestrów diagnostycznych w firmware karty - mapa rejestrów ELA01 |
| `DEV.<device_id>.WATCHDOG_OK` | DEVICE HEALTH | SYSTEM INPUT | czeka na firmware | wymaga rejestrów diagnostycznych w firmware karty - mapa rejestrów ELA01 |
| `DEV.<device_id>.WATCHDOG_FAULT` | DEVICE HEALTH | SYSTEM INPUT | czeka na firmware | wymaga rejestrów diagnostycznych w firmware karty - mapa rejestrów ELA01 |
| `DEV.<device_id>.POWER_OK` | DEVICE HEALTH | SYSTEM INPUT | czeka na firmware | wymaga rejestrów diagnostycznych w firmware karty - mapa rejestrów ELA01 |
| `DEV.<device_id>.CONFIG_OK` | DEVICE HEALTH | SYSTEM INPUT | czeka na firmware | wymaga rejestrów diagnostycznych w firmware karty - mapa rejestrów ELA01 |
| `DEV.<device_id>.MAINTENANCE` | DEVICE HEALTH | SYSTEM INPUT | czeka na firmware | wymaga rejestrów diagnostycznych w firmware karty - mapa rejestrów ELA01 |
| `DEV.<device_id>.SIMULATION` | DEVICE HEALTH | SYSTEM INPUT | czeka na firmware | wymaga rejestrów diagnostycznych w firmware karty - mapa rejestrów ELA01 |
| `SEC.SYSTEM.ARMED` | SECURITY | SYSTEM INPUT | w katalogu i obsłużony |  |
| `SEC.SYSTEM.DISARMED` | SECURITY | SYSTEM INPUT | w katalogu i obsłużony |  |
| `SEC.SYSTEM.ALARM` | SECURITY | SYSTEM INPUT | w katalogu i obsłużony |  |
| `SEC.SYSTEM.TECHNICAL_ALARM` | SECURITY | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `SEC.SYSTEM.TAMPER` | SECURITY | SYSTEM INPUT | w katalogu i obsłużony |  |
| `SEC.SYSTEM.FAULT` | SECURITY | SYSTEM INPUT | w katalogu i obsłużony |  |
| `SEC.SYSTEM.ENTRY_DELAY` | SECURITY | SYSTEM INPUT | w katalogu i obsłużony |  |
| `SEC.SYSTEM.EXIT_DELAY` | SECURITY | SYSTEM INPUT | w katalogu i obsłużony |  |
| `SEC.SYSTEM.ANY_ZONE_ARMED` | SECURITY | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `SEC.SYSTEM.ANY_ZONE_ALARM` | SECURITY | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `SEC.SYSTEM.ANY_LINE_VIOLATED` | SECURITY | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `SEC.SYSTEM.ANY_LINE_FAULT` | SECURITY | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `SEC.SYSTEM.ALARM_MEMORY` | SECURITY | SYSTEM INPUT | w katalogu i obsłużony |  |
| `SEC.SYSTEM.WALK_TEST` | SECURITY | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `SEC.ZONE.<zone_id>.ARMED` | SECURITY | SYSTEM INPUT | w katalogu i obsłużony |  |
| `SEC.ZONE.<zone_id>.DISARMED` | SECURITY | SYSTEM INPUT | w katalogu i obsłużony |  |
| `SEC.ZONE.<zone_id>.ALARM` | SECURITY | SYSTEM INPUT | w katalogu i obsłużony |  |
| `SEC.ZONE.<zone_id>.ENTRY_DELAY` | SECURITY | SYSTEM INPUT | w katalogu i obsłużony |  |
| `SEC.ZONE.<zone_id>.EXIT_DELAY` | SECURITY | SYSTEM INPUT | w katalogu i obsłużony |  |
| `SEC.ZONE.<zone_id>.FAULT` | SECURITY | SYSTEM INPUT | w katalogu i obsłużony |  |
| `SEC.ZONE.<zone_id>.BYPASSED` | SECURITY | SYSTEM INPUT | w katalogu i obsłużony |  |
| `SEC.ZONE.<zone_id>.ALARM_MEMORY` | SECURITY | SYSTEM INPUT | w katalogu i obsłużony |  |
| `SEC.ZONE.<zone_id>.WALK_TEST` | SECURITY | SYSTEM INPUT | w katalogu i obsłużony |  |
| `SEC.ZONE.<zone_id>.INHIBITED` | SECURITY | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `SEC.LINE.<line_id>.SECURE` | SECURITY | SYSTEM INPUT | w katalogu i obsłużony |  |
| `SEC.LINE.<line_id>.VIOLATED` | SECURITY | SYSTEM INPUT | w katalogu i obsłużony |  |
| `SEC.LINE.<line_id>.FAULT` | SECURITY | SYSTEM INPUT | w katalogu i obsłużony |  |
| `SEC.LINE.<line_id>.TAMPER` | SECURITY | SYSTEM INPUT | w katalogu i obsłużony |  |
| `SEC.LINE.<line_id>.SHORT` | SECURITY | SYSTEM INPUT | w katalogu i obsłużony |  |
| `SEC.LINE.<line_id>.OPEN_FAULT` | SECURITY | SYSTEM INPUT | w katalogu i obsłużony |  |
| `SEC.LINE.<line_id>.UNDETERMINED` | SECURITY | SYSTEM INPUT | w katalogu i obsłużony |  |
| `SEC.LINE.<line_id>.BYPASSED` | SECURITY | SYSTEM INPUT | w katalogu i obsłużony |  |
| `SEC.LINE.<line_id>.SUSPECT` | SECURITY | SYSTEM INPUT | w katalogu i obsłużony |  |
| `SEC.LINE.<line_id>.WALK_TEST_SEEN` | SECURITY | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `PROT.READY` | PROTECTION | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `PROT.ACTIVE` | PROTECTION | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `PROT.ANY_START` | PROTECTION | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `PROT.ANY_TRIP` | PROTECTION | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `PROT.BLOCKED` | PROTECTION | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `PROT.FAIL` | PROTECTION | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `PROT.UNDERVOLTAGE` | PROTECTION | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `PROT.OVERVOLTAGE` | PROTECTION | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `PROT.OVERCURRENT` | PROTECTION | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `PROT.PHASE_LOSS` | PROTECTION | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `PROT.PHASE_SEQUENCE_FAULT` | PROTECTION | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `PROT.UNBALANCE` | PROTECTION | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `PROT.UNDERFREQUENCY` | PROTECTION | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `PROT.OVERFREQUENCY` | PROTECTION | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `PROT.EARTH_FAULT` | PROTECTION | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `PROT.NEUTRAL_FAULT` | PROTECTION | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `PROT.POWER_REVERSE` | PROTECTION | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `PROT.<stage_id>.ENABLED` | PROTECTION | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `PROT.<stage_id>.START` | PROTECTION | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `PROT.<stage_id>.TRIP` | PROTECTION | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `PROT.<stage_id>.BLOCKED` | PROTECTION | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `PWR.MAINS_OK` | POWER | SYSTEM INPUT | czeka na sprzęt | wymaga nadania roli punktowi w Studio (zasilanie) - osobne zadanie |
| `PWR.MAINS_LOST` | POWER | SYSTEM INPUT | czeka na sprzęt | wymaga nadania roli punktowi w Studio (zasilanie) - osobne zadanie |
| `PWR.L1_OK` | POWER | SYSTEM INPUT | czeka na sprzęt | wymaga nadania roli punktowi w Studio (zasilanie) - osobne zadanie |
| `PWR.L2_OK` | POWER | SYSTEM INPUT | czeka na sprzęt | wymaga nadania roli punktowi w Studio (zasilanie) - osobne zadanie |
| `PWR.L3_OK` | POWER | SYSTEM INPUT | czeka na sprzęt | wymaga nadania roli punktowi w Studio (zasilanie) - osobne zadanie |
| `PWR.NEUTRAL_OK` | POWER | SYSTEM INPUT | czeka na sprzęt | wymaga nadania roli punktowi w Studio (zasilanie) - osobne zadanie |
| `PWR.PHASE_SEQUENCE_OK` | POWER | SYSTEM INPUT | czeka na sprzęt | wymaga nadania roli punktowi w Studio (zasilanie) - osobne zadanie |
| `PWR.POWER_24V_OK` | POWER | SYSTEM INPUT | czeka na sprzęt | wymaga nadania roli punktowi w Studio (zasilanie) - osobne zadanie |
| `PWR.POWER_24V_FAULT` | POWER | SYSTEM INPUT | czeka na sprzęt | wymaga nadania roli punktowi w Studio (zasilanie) - osobne zadanie |
| `PWR.DC_BUS_OK` | POWER | SYSTEM INPUT | czeka na sprzęt | wymaga nadania roli punktowi w Studio (zasilanie) - osobne zadanie |
| `PWR.AUX_POWER_OK` | POWER | SYSTEM INPUT | czeka na sprzęt | wymaga nadania roli punktowi w Studio (zasilanie) - osobne zadanie |
| `PWR.BACKUP_AVAILABLE` | POWER | SYSTEM INPUT | czeka na sprzęt | wymaga nadania roli punktowi w Studio (zasilanie) - osobne zadanie |
| `PWR.BACKUP_ACTIVE` | POWER | SYSTEM INPUT | czeka na sprzęt | wymaga nadania roli punktowi w Studio (zasilanie) - osobne zadanie |
| `UPS.ONLINE` | UPS | SYSTEM INPUT | czeka na sprzęt | wymaga nadania roli punktowi w Studio (UPS) - osobne zadanie |
| `UPS.ON_BATTERY` | UPS | SYSTEM INPUT | czeka na sprzęt | wymaga nadania roli punktowi w Studio (UPS) - osobne zadanie |
| `UPS.BYPASS` | UPS | SYSTEM INPUT | czeka na sprzęt | wymaga nadania roli punktowi w Studio (UPS) - osobne zadanie |
| `UPS.LOW_BATTERY` | UPS | SYSTEM INPUT | czeka na sprzęt | wymaga nadania roli punktowi w Studio (UPS) - osobne zadanie |
| `UPS.BATTERY_FAULT` | UPS | SYSTEM INPUT | czeka na sprzęt | wymaga nadania roli punktowi w Studio (UPS) - osobne zadanie |
| `UPS.OVERLOAD` | UPS | SYSTEM INPUT | czeka na sprzęt | wymaga nadania roli punktowi w Studio (UPS) - osobne zadanie |
| `UPS.FAULT` | UPS | SYSTEM INPUT | czeka na sprzęt | wymaga nadania roli punktowi w Studio (UPS) - osobne zadanie |
| `UPS.MAINS_PRESENT` | UPS | SYSTEM INPUT | czeka na sprzęt | wymaga nadania roli punktowi w Studio (UPS) - osobne zadanie |
| `ALM.ANY_ACTIVE` | PROCESS ALARMS | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `ALM.ANY_UNACK` | PROCESS ALARMS | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `ALM.ANY_CRITICAL` | PROCESS ALARMS | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `ALM.ANY_WARNING` | PROCESS ALARMS | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `ALM.NEW_ALARM` | PROCESS ALARMS | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `ALM.HORN_REQUIRED` | PROCESS ALARMS | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `ALM.SYSTEM_FAULT` | PROCESS ALARMS | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `ALM.<alarm_id>.ACTIVE` | PROCESS ALARMS | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `ALM.<alarm_id>.ACKNOWLEDGED` | PROCESS ALARMS | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `ALM.<alarm_id>.LATCHED` | PROCESS ALARMS | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `MODE.NORMAL` | MODES | SYSTEM INPUT | w katalogu i obsłużony |  |
| `MODE.AUTO` | MODES | SYSTEM INPUT | w katalogu i obsłużony |  |
| `MODE.MANUAL` | MODES | SYSTEM INPUT | w katalogu i obsłużony |  |
| `MODE.LOCAL` | MODES | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `MODE.REMOTE` | MODES | SYSTEM INPUT | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `MODE.SERVICE` | MODES | SYSTEM INPUT | w katalogu i obsłużony |  |
| `MODE.MAINTENANCE` | MODES | SYSTEM INPUT | w katalogu i obsłużony |  |
| `MODE.TEST` | MODES | SYSTEM INPUT | w katalogu i obsłużony |  |
| `MODE.TRAINING` | MODES | SYSTEM INPUT | w katalogu i obsłużony |  |
| `MODE.SIMULATION` | MODES | SYSTEM INPUT | w katalogu i obsłużony |  |
| `MODE.EMERGENCY` | MODES | SYSTEM INPUT | w katalogu i obsłużony |  |
| `MODE.DEGRADED` | MODES | SYSTEM INPUT | w katalogu i obsłużony |  |
| `DIAG.ANY_FAULT` | DIAGNOSTICS | SYSTEM INPUT | czeka na firmware | wymaga rejestrów diagnostycznych w firmware karty - mapa rejestrów ELA01 |
| `DIAG.IO_FAULT` | DIAGNOSTICS | SYSTEM INPUT | czeka na firmware | wymaga rejestrów diagnostycznych w firmware karty - mapa rejestrów ELA01 |
| `DIAG.DRIVER_FAULT` | DIAGNOSTICS | SYSTEM INPUT | czeka na firmware | wymaga rejestrów diagnostycznych w firmware karty - mapa rejestrów ELA01 |
| `DIAG.CONFIG_FAULT` | DIAGNOSTICS | SYSTEM INPUT | czeka na firmware | wymaga rejestrów diagnostycznych w firmware karty - mapa rejestrów ELA01 |
| `DIAG.LOGIC_FAULT` | DIAGNOSTICS | SYSTEM INPUT | czeka na firmware | wymaga rejestrów diagnostycznych w firmware karty - mapa rejestrów ELA01 |
| `DIAG.SYNOPTIC_FAULT` | DIAGNOSTICS | SYSTEM INPUT | czeka na firmware | wymaga rejestrów diagnostycznych w firmware karty - mapa rejestrów ELA01 |
| `DIAG.DATABASE_FAULT` | DIAGNOSTICS | SYSTEM INPUT | czeka na firmware | wymaga rejestrów diagnostycznych w firmware karty - mapa rejestrów ELA01 |
| `DIAG.HISTORIAN_FAULT` | DIAGNOSTICS | SYSTEM INPUT | czeka na firmware | wymaga rejestrów diagnostycznych w firmware karty - mapa rejestrów ELA01 |
| `DIAG.API_FAULT` | DIAGNOSTICS | SYSTEM INPUT | czeka na firmware | wymaga rejestrów diagnostycznych w firmware karty - mapa rejestrów ELA01 |
| `DIAG.TIME_FAULT` | DIAGNOSTICS | SYSTEM INPUT | czeka na firmware | wymaga rejestrów diagnostycznych w firmware karty - mapa rejestrów ELA01 |
| `DIAG.WATCHDOG_FAULT` | DIAGNOSTICS | SYSTEM INPUT | czeka na firmware | wymaga rejestrów diagnostycznych w firmware karty - mapa rejestrów ELA01 |
| `DIAG.DISK_WARNING` | DIAGNOSTICS | SYSTEM INPUT | czeka na firmware | wymaga rejestrów diagnostycznych w firmware karty - mapa rejestrów ELA01 |
| `DIAG.DISK_FULL` | DIAGNOSTICS | SYSTEM INPUT | czeka na firmware | wymaga rejestrów diagnostycznych w firmware karty - mapa rejestrów ELA01 |
| `DIAG.HIGH_CPU` | DIAGNOSTICS | SYSTEM INPUT | czeka na firmware | wymaga rejestrów diagnostycznych w firmware karty - mapa rejestrów ELA01 |
| `DIAG.HIGH_TEMP` | DIAGNOSTICS | SYSTEM INPUT | czeka na firmware | wymaga rejestrów diagnostycznych w firmware karty - mapa rejestrów ELA01 |
| `REQ.SEC.ARM_ALL` | REQ SECURITY | SYSTEM OUTPUT / REQUEST | w katalogu i obsłużony |  |
| `REQ.SEC.DISARM_ALL` | REQ SECURITY | SYSTEM OUTPUT / REQUEST | w katalogu i obsłużony |  |
| `REQ.SEC.CLEAR_ALARM_MEMORY` | REQ SECURITY | SYSTEM OUTPUT / REQUEST | w katalogu i obsłużony |  |
| `REQ.SEC.SILENCE` | REQ SECURITY | SYSTEM OUTPUT / REQUEST | w katalogu i obsłużony |  |
| `REQ.SEC.ZONE.<zone_id>.ARM` | REQ SECURITY | SYSTEM OUTPUT / REQUEST | w katalogu i obsłużony |  |
| `REQ.SEC.ZONE.<zone_id>.DISARM` | REQ SECURITY | SYSTEM OUTPUT / REQUEST | w katalogu i obsłużony |  |
| `REQ.SEC.ZONE.<zone_id>.BYPASS` | REQ SECURITY | SYSTEM OUTPUT / REQUEST | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `REQ.SEC.ZONE.<zone_id>.UNBYPASS` | REQ SECURITY | SYSTEM OUTPUT / REQUEST | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `REQ.SEC.ZONE.<zone_id>.CLEAR_MEMORY` | REQ SECURITY | SYSTEM OUTPUT / REQUEST | w katalogu i obsłużony |  |
| `REQ.SEC.ZONE.<zone_id>.START_WALK_TEST` | REQ SECURITY | SYSTEM OUTPUT / REQUEST | w katalogu i obsłużony |  |
| `REQ.SEC.ZONE.<zone_id>.STOP_WALK_TEST` | REQ SECURITY | SYSTEM OUTPUT / REQUEST | w katalogu i obsłużony |  |
| `REQ.SEC.ZONE.<zone_id>.INHIBIT` | REQ SECURITY | SYSTEM OUTPUT / REQUEST | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `REQ.SEC.ZONE.<zone_id>.UNINHIBIT` | REQ SECURITY | SYSTEM OUTPUT / REQUEST | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `REQ.MODE.NORMAL` | REQ MODES | SYSTEM OUTPUT / REQUEST | w katalogu i obsłużony |  |
| `REQ.MODE.AUTO` | REQ MODES | SYSTEM OUTPUT / REQUEST | w katalogu i obsłużony |  |
| `REQ.MODE.MANUAL` | REQ MODES | SYSTEM OUTPUT / REQUEST | w katalogu i obsłużony |  |
| `REQ.MODE.SERVICE` | REQ MODES | SYSTEM OUTPUT / REQUEST | w katalogu i obsłużony |  |
| `REQ.MODE.MAINTENANCE` | REQ MODES | SYSTEM OUTPUT / REQUEST | w katalogu i obsłużony |  |
| `REQ.MODE.TEST` | REQ MODES | SYSTEM OUTPUT / REQUEST | w katalogu i obsłużony |  |
| `REQ.MODE.EMERGENCY` | REQ MODES | SYSTEM OUTPUT / REQUEST | w katalogu i obsłużony |  |
| `REQ.ALM.ACK_ALL` | REQ ALARMS | SYSTEM OUTPUT / REQUEST | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `REQ.ALM.SILENCE_HORN` | REQ ALARMS | SYSTEM OUTPUT / REQUEST | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `REQ.ALM.RESET` | REQ ALARMS | SYSTEM OUTPUT / REQUEST | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `REQ.ALM.TEST` | REQ ALARMS | SYSTEM OUTPUT / REQUEST | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `REQ.PROT.RESET` | REQ PROTECTION | SYSTEM OUTPUT / REQUEST | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `REQ.PROT.RESET_LATCH` | REQ PROTECTION | SYSTEM OUTPUT / REQUEST | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `REQ.PROT.TEST` | REQ PROTECTION | SYSTEM OUTPUT / REQUEST | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `REQ.PROT.<stage_id>.BLOCK` | REQ PROTECTION | SYSTEM OUTPUT / REQUEST | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `REQ.PROT.<stage_id>.UNBLOCK` | REQ PROTECTION | SYSTEM OUTPUT / REQUEST | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `REQ.DEV.<device_id>.RESET` | REQ DEVICE | SYSTEM OUTPUT / REQUEST | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `REQ.DEV.<device_id>.RECONNECT` | REQ DEVICE | SYSTEM OUTPUT / REQUEST | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `REQ.DEV.<device_id>.RESYNC` | REQ DEVICE | SYSTEM OUTPUT / REQUEST | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `REQ.SYSTEM.RESTART_RUNTIME` | REQ SYSTEM | SYSTEM OUTPUT / REQUEST | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `REQ.SYSTEM.RELOAD_LOGIC` | REQ SYSTEM | SYSTEM OUTPUT / REQUEST | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `REQ.SYSTEM.RELOAD_SYNOPTIC` | REQ SYSTEM | SYSTEM OUTPUT / REQUEST | do zrobienia | w zakresie katalogu, jeszcze nie dodany |
| `LINK.<link_id>.IN01..IN32` | INTER-CONTROLLER | SYSTEM INPUT | przyszłość | sygnały między sterownikami, bez implementacji |
| `LINK.<link_id>.OUT01..OUT32` | INTER-CONTROLLER | SYSTEM OUTPUT / REQUEST | przyszłość | sygnały między sterownikami, bez implementacji |
| `M.USER.<name>` | USER INTERNAL | USER INTERNAL | poza katalogiem | to markery użytkownika (M.*) z działu Sygnały, nie katalog platformy |
| `M.RET.<name>` | USER INTERNAL | USER INTERNAL | poza katalogiem | to markery użytkownika (M.*) z działu Sygnały, nie katalog platformy |
| `ELA<nn>.DI<nn>` | PHYSICAL I/O | PHYSICAL INPUT | poza katalogiem | adres fizyczny, opisany gramatyką adresów (shared/addressing.py) |
| `ADA<nn>.DO<nn>` | PHYSICAL I/O | PHYSICAL OUTPUT | poza katalogiem | adres fizyczny, opisany gramatyką adresów (shared/addressing.py) |

## W katalogu, poza rejestrem (27)

Sygnały, które platforma udostępnia, a których rejestr nie opisuje —
kandydaci do dopisania do arkusza.

- `REQ.SEC.ARM_ALL_PARTIAL`
- `SEC.SYSTEM.ACTIVE_COUNT`
- `SEC.SYSTEM.ALARM_LATCHED`
- `SEC.SYSTEM.ARMED_PARTIAL`
- `SEC.SYSTEM.DELAY_REMAINING`
- `SEC.SYSTEM.LAST_TRIGGER`
- `SEC.SYSTEM.PANIC`
- `SEC.SYSTEM.READY_TO_ARM`
- `SEC.SYSTEM.SIREN_ACTIVE`
- `SEC.SYSTEM.SIREN_TIME_LEFT`
- `SEC.SYSTEM.STROBE_ACTIVE`
- `SYS.ACCESS_ENGINEER`
- `SYS.ACCESS_LEVEL`
- `SYS.ACCESS_OPERATOR`
- `SYS.ACCESS_USER`
- `SYS.BLINK_FAST`
- `SYS.BLINK_SLOW`
- `SYS.COMMS_OK`
- `SYS.CYCLE_COUNT`
- `SYS.FAULT`
- `SYS.HEALTH`
- `SYS.PULSE_100MS`
- `SYS.PULSE_1S`
- `SYS.PULSE_500MS`
- `SYS.SCAN_OVERRUN`
- `SYS.SCAN_TIME`
- `SYS.TRAINING_MODE`

