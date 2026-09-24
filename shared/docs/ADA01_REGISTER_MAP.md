# ADA01 — mapa rejestrów zabezpieczeń (kontrakt)

**Kontrakt dla przyszłego firmware karty ADA01.** Sterownik (EPW-OS) tę
mapę czyta i wystawia z niej bity `PROT.*` rejestru sygnałów; emulacja
(`runtime/tools/device_emulation.py`) realizuje tę samą mapę na wirtualnej
magistrali, więc driver, bity i logika są napisane raz. Wersja wykonywalna
mapy: `runtime/epw_os/drivers/device_blocks.py`; lista stopni:
`shared/logic/protection_stages.py`.

Zasada Z3: **o zadziałaniu decyduje ADA01.** Sterownik czyta słowa statusu
i niczego nie porównuje z nastawami. Zasada Z4: gdy karta nie odpowiada,
bity przyjmują wartość bezpieczną (`PROT.FAIL = TRUE`, reszta FALSE),
a `COMM.<karta>.ONLINE = FALSE`.

Adresy są adresami rejestrów Modbus (od 0, jak w PDU). Rejestry wejściowe
czytane FC4, rejestry komend pisane FC6. Karta bez danego bloku odpowiada
wyjątkiem Modbus 2 (illegal address) — to nie błąd komunikacji; sterownik
przestaje pytać o blok na 30 s.

## Rejestry wejściowe (FC4) — blok PROT, adresy 100–132

| adres | nazwa | znaczenie |
|---:|---|---|
| 100 | `PROT_STATUS` | słowo statusu zbiorczego (bity niżej) |
| 101 | `PROT_FIRMWARE` | wersja firmware: `major << 8 \| minor` |
| 102 | `PROT_FIRMWARE_BUILD` | numer kompilacji |
| 103 | `PROT_CHECKSUM_LO` | CRC-16 nastaw (algorytm niżej), słowo młodsze |
| 104 | `PROT_CHECKSUM_HI` | zarezerwowane (0) |
| 105–109 | — | zarezerwowane |
| 110 + i | `PROT_STAGE_BASE + i` | słowo statusu stopnia o indeksie *i* (tabela stopni niżej) |

### Bity `PROT_STATUS` (adres 100)

| bit | nazwa | sygnał rejestru |
|---:|---|---|
| 0 | READY | `PROT.READY` |
| 1 | ACTIVE | `PROT.ACTIVE` |
| 2 | BLOCKED | `PROT.BLOCKED` (dowolny stopień zablokowany) |
| 3 | FAIL | `PROT.FAIL` |
| 4 | ANY_START | `PROT.ANY_START` |
| 5 | ANY_TRIP | `PROT.ANY_TRIP` |
| 6 | TEST_ACTIVE | `PROT.TEST_ACTIVE` (trwa autotest) |
| 7 | TEST_OK | `PROT.TEST_OK` (ostatni autotest poprawny) |
| 8 | ANY_LATCHED | dowolny stopień zatrzaśnięty |

### Bity słowa stopnia (adresy 110–132)

| bit | nazwa | sygnał rejestru |
|---:|---|---|
| 0 | ENABLED | `PROT.<stopień>.ENABLED` |
| 1 | START | `PROT.<stopień>.START` (pobudzenie) |
| 2 | TRIP | `PROT.<stopień>.TRIP` (zadziałanie) |
| 3 | BLOCKED | `PROT.<stopień>.BLOCKED` |
| 4 | LATCHED | `PROT.<stopień>.LATCHED` (zatrzask do `REQ.PROT.RESET_LATCH`) |

Zadziałanie jest **zatrzaskiwane w karcie**: stopień trzyma TRIP i LATCHED
do komendy RESET_LATCH. Dzięki temu po restarcie sterownika informacja
wraca z urządzenia, a nie z pamięci sterownika.

### Tabela stopni (indeks = adres − 110)

| i | id stopnia | funkcja | stopień | bit zbiorczy |
|---:|---|---|---|---|
| 0 | `UV_STAGE1` | 27 Under Voltage | Stage 1 | `PROT.UNDERVOLTAGE` |
| 1 | `UV_STAGE2` | 27 Under Voltage | Stage 2 | `PROT.UNDERVOLTAGE` |
| 2 | `OV_STAGE1` | 59 Over Voltage | Stage 1 | `PROT.OVERVOLTAGE` |
| 3 | `OV_STAGE2` | 59 Over Voltage | Stage 2 | `PROT.OVERVOLTAGE` |
| 4 | `OVN_STAGE1` | 59N Neutral Overvoltage | Stage 1 | `PROT.NEUTRAL_FAULT` |
| 5 | `PHSEQ_STAGE1` | 47 Phase Sequence / Phase Loss | Stage 1 | `PROT.PHASE_LOSS`, `PROT.PHASE_SEQUENCE_FAULT` |
| 6 | `UF_STAGE1` | 81U Under Frequency | Stage 1 | `PROT.UNDERFREQUENCY` |
| 7 | `UF_STAGE2` | 81U Under Frequency | Stage 2 | `PROT.UNDERFREQUENCY` |
| 8 | `OF_STAGE1` | 81O Over Frequency | Stage 1 | `PROT.OVERFREQUENCY` |
| 9 | `OF_STAGE2` | 81O Over Frequency | Stage 2 | `PROT.OVERFREQUENCY` |
| 10 | `IOC_STAGE1` | 50 Instantaneous Overcurrent | Stage 1 | `PROT.OVERCURRENT` |
| 11 | `IOC_STAGE2` | 50 Instantaneous Overcurrent | Stage 2 | `PROT.OVERCURRENT` |
| 12 | `TOC_STAGE1` | 51 Time Overcurrent | Stage 1 | `PROT.OVERCURRENT` |
| 13 | `TOC_STAGE2` | 51 Time Overcurrent | Stage 2 | `PROT.OVERCURRENT` |
| 14 | `NEGSEQ_STAGE1` | 46 Negative Sequence Current | Stage 1 | `PROT.UNBALANCE` |
| 15 | `THERMAL_STAGE1` | 49 Thermal Overload | Stage 1 | `PROT.THERMAL_OVERLOAD` |
| 16 | `THERMAL_STAGE2` | 49 Thermal Overload | Stage 2 | `PROT.THERMAL_OVERLOAD` |
| 17 | `IEF_STAGE1` | 50N Earth Fault Instantaneous | Stage 1 | `PROT.EARTH_FAULT` |
| 18 | `TEF_STAGE1` | 51N Earth Fault Time | Stage 1 | `PROT.EARTH_FAULT` |
| 19 | `CTRLV_STAGE1` | Control Voltage Loss | Stage 1 | `PROT.CONTROL_VOLTAGE_LOSS` |
| 20 | `TECHV_STAGE1` | Technical Supply Loss | Stage 1 | `PROT.TECHNICAL_SUPPLY_LOSS` |
| 21 | `UPSV_STAGE1` | UPS Supply Loss | Stage 1 | `PROT.UPS_SUPPLY_LOSS` |
| 22 | `RPWR_STAGE1` | 32 Reverse Power | Stage 1 | `PROT.POWER_REVERSE` |

Decyzja właściciela (2026-09-24): funkcja 32 (moc zwrotna) dostała stopień
`RPWR_STAGE1` (indeks 22, adres 132), a stopnie 49 i zaniki zasilań — bity
zbiorcze nazwane gramatyką rejestru (przyjęte tego samego dnia).

## Rejestry komend (FC6) — adresy 200–202

| adres | nazwa | wartość | działanie | sygnał rejestru |
|---:|---|---:|---|---|
| 200 | `PROT_CMD` | 1 | RESET — kasuje pobudzenia i zadziałania (bez zatrzasku) | `REQ.PROT.RESET` |
| 200 | `PROT_CMD` | 2 | RESET_LATCH — kasuje zatrzaśnięte zadziałania | `REQ.PROT.RESET_LATCH` |
| 200 | `PROT_CMD` | 3 | SELFTEST — autotest; TEST_ACTIVE na czas testu, potem TEST_OK | `REQ.PROT.TEST` |
| 201 | `PROT_BLOCK_STAGE` | i + 1 | blokuje stopień o indeksie *i* | `REQ.PROT.<stopień>.BLOCK` |
| 202 | `PROT_UNBLOCK_STAGE` | i + 1 | odblokowuje stopień o indeksie *i* | `REQ.PROT.<stopień>.UNBLOCK` |

Poziomy dostępu (te same z logiki i z panelu): RESET / RESET_LATCH / TEST —
Operator; BLOCK / UNBLOCK — Engineer. Każde wykonanie i każda odmowa
(brak karty ADA w projekcie, karta nie odpowiada, zapis nieudany) trafia do
dziennika audytowego (`PROTECTION_REQUEST`, `PROTECTION_REQUEST_REFUSED`).

## Suma kontrolna nastaw

CRC-16 (wielomian Modbus 0xA001, init 0xFFFF) z ciągu UTF-8 powstałego przez
sklejenie średnikiem, w kolejności tabeli stopni, wpisów
`<id>:<enabled 0/1>:<setting %.3f>:<hysteresis %.3f>:<delay_ms>:<action>`.
Stopnie nieobecne w nastawach projektu liczone są z wartościami domyślnymi
(`enabled=1, 0.000, 0.000, 0, Trip`). Implementacja:
`shared.logic.protection_stages.settings_checksum()`.

Sterownik liczy tę sumę z nastaw projektu (`electrical_protection_stages`
w `projekt.epw`) i porównuje z rejestrem 103. **Rozjazd = alarm**
(`PROT_SETTINGS_MISMATCH_<karta>`, priorytet 3) i `PROT.SETTINGS_MISMATCH =
TRUE`, dopóki trwa. Per stopień: gdy `ENABLED` w karcie różni się od
`enabled` w projekcie, ostrzeżenie w logu — **decyduje karta**, projekt jest
nieaktualny.

## Blok diagnostyczny

ADA01 udostępnia także blok DIAG (adresy 500–504, komendy 600) — patrz
`CARD_DIAGNOSTIC_REGISTER_MAP.md`.
