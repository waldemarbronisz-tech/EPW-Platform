# ELA01 / ADA01 / EPM — mapa rejestrów diagnostycznych (kontrakt)

**Kontrakt dla przyszłego firmware kart.** Każda karta na magistrali
udostępnia ten sam blok DIAG; sterownik wystawia z niego bity
`DEV.<karta>.*` oraz zbiorcze `DIAG.*`. Emulacja:
`runtime/tools/device_emulation.py`, `CardDiagEmulator`. Wersja wykonywalna:
`runtime/epw_os/drivers/device_blocks.py`.

Zasada Z4: karta, która nie odpowiada, daje `DEV.<karta>.FAULT = TRUE`
i `DEV.<karta>.WATCHDOG_FAULT = TRUE`, pozostałe `DEV.<karta>.*` FALSE,
a `COMM.<karta>.ONLINE = FALSE`.

## Rejestry wejściowe (FC4) — blok DIAG, adresy 500–504

| adres | nazwa | jednostka | znaczenie |
|---:|---|---|---|
| 500 | `DIAG_STATUS` | | słowo statusu karty (bity niżej) |
| 501 | `DIAG_FIRMWARE` | | wersja firmware: `major << 8 \| minor` |
| 502 | `DIAG_TEMPERATURE` | °C × 10, ze znakiem | temperatura karty |
| 503 | `DIAG_SUPPLY` | V × 100 | napięcie zasilania karty |
| 504 | `DIAG_ERRORS` | | licznik błędów od włączenia |

### Bity `DIAG_STATUS` (adres 500)

| bit | nazwa | sygnał rejestru |
|---:|---|---|
| 0 | READY | `DEV.<karta>.READY` |
| 1 | RUNNING | `DEV.<karta>.RUNNING` |
| 2 | FAULT | `DEV.<karta>.FAULT` |
| 3 | WATCHDOG_OK | `DEV.<karta>.WATCHDOG_OK`; `DEV.<karta>.WATCHDOG_FAULT` = negacja |
| 4 | POWER_OK | `DEV.<karta>.POWER_OK` |
| 5 | CONFIG_OK | `DEV.<karta>.CONFIG_OK` |
| 6 | MAINTENANCE | `DEV.<karta>.MAINTENANCE` |
| 7 | SIMULATION | `DEV.<karta>.SIMULATION` (karta emulowana ustawia ten bit) |
| 8 | IO_FAULT | awaria toru wejść/wyjść karty (wchodzi w `DIAG.IO_FAULT`) |

## Rejestr komend (FC6) — adres 600

| adres | nazwa | wartość | działanie | sygnał rejestru |
|---:|---|---:|---|---|
| 600 | `DIAG_CMD` | 1 | RESET — karta restartuje się, kasuje FAULT/IO_FAULT i licznik błędów | `REQ.DEV.<karta>.RESET` |
| 600 | `DIAG_CMD` | 2 | RESYNC — karta ponownie wczytuje konfigurację | `REQ.DEV.<karta>.RESYNC` |

`REQ.DEV.<karta>.RECONNECT` nie dotyczy karty: sterownik zamyka i otwiera
od nowa magistralę i zeruje liczniki komunikacji tej karty. Wszystkie trzy
żądania — Engineer; wykonanie i odmowa w dzienniku audytowym
(`DEVICE_REQUEST`, `DEVICE_REQUEST_REFUSED`).

## Bity zbiorcze `DIAG.*` (sterownik)

| sygnał | źródło |
|---|---|
| `DIAG.IO_FAULT` | `DEV.<karta>.FAULT` którejś karty albo `COMM.ANY_DEVICE_FAULT` |
| `DIAG.WATCHDOG_FAULT` | `DEV.<karta>.WATCHDOG_FAULT` którejś karty |
| `DIAG.DRIVER_FAULT` | `COMM.BUS_FAULT` albo podsystem DRIVERS w stanie FAULT |
| `DIAG.CONFIG_FAULT` | `SYS.CONFIG_FAULT` albo `DEV.<karta>.CONFIG_OK = FALSE` u odpowiadającej karty |
| `DIAG.LOGIC_FAULT` | `RT.LOGIC.FAIL` albo `RT.LOGIC.PROJECT_FAULT` |
| `DIAG.SYNOPTIC_FAULT` | `RT.SYNOPTIC.FAIL` albo `RT.SYNOPTIC.BINDING_FAULT` |
| `DIAG.DATABASE_FAULT` | podsystem DATABASE w stanie FAULT |
| `DIAG.HISTORIAN_FAULT` | podsystem HISTORIAN w stanie FAULT albo DEGRADED |
| `DIAG.API_FAULT` | podsystem API w stanie FAULT, albo nie RUNNING po starcie |
| `DIAG.TIME_FAULT` | `SYS.TIME_SYNC_FAULT` |
| `DIAG.DISK_WARNING` / `DIAG.DISK_FULL` | zapełnienie dysku sterownika ≥ 90 % / ≥ 98 % |
| `DIAG.HIGH_CPU` | średnie obciążenie 1 min > 0,9 na rdzeń (tam, gdzie system je podaje — Linux) |
| `DIAG.HIGH_TEMP` | `DIAG_TEMPERATURE` którejś karty > 70 °C albo czujnik SoC (`/sys/class/thermal`) > 75 °C |
| `DIAG.ANY_FAULT` | dowolny z powyższych |
