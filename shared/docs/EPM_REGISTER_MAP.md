# EPM — mapa rejestrów zasilania (kontrakt)

**Kontrakt dla przyszłego firmware miernika EPM.** Sterownik czyta blok
POWER i wystawia z niego bity `PWR.*`; emulacja
(`runtime/tools/device_emulation.py`, `EpmEmulator`) realizuje tę samą mapę.
Wersja wykonywalna: `runtime/epw_os/drivers/device_blocks.py`.

Karta EPM w projekcie Studia nie ma kanałów DI/DO/AI/AO — jest na
magistrali wyłącznie dla swoich bloków rejestrów (i dostaje własne tagi
`<id>.UL1.RMS`, `<id>.UL2.RMS`, `<id>.UL3.RMS`, `<id>.FREQ`).

Zasada Z4: gdy EPM nie odpowiada, `PWR.MAINS_LOST = TRUE`,
`PWR.POWER_24V_FAULT = TRUE`, pozostałe `PWR.*` FALSE, a
`COMM.<EPM>.ONLINE = FALSE`.

## Rejestry wejściowe (FC4) — blok POWER, adresy 0–10

| adres | nazwa | jednostka | znaczenie |
|---:|---|---|---|
| 0 | `POWER_UL1` | V × 10 | napięcie fazowe L1 (RMS) |
| 1 | `POWER_UL2` | V × 10 | napięcie fazowe L2 (RMS) |
| 2 | `POWER_UL3` | V × 10 | napięcie fazowe L3 (RMS) |
| 3 | `POWER_FREQ` | Hz × 100 | częstotliwość sieci |
| 4 | `POWER_UN` | V × 10 | napięcie N–PE |
| 5–9 | — | | zarezerwowane |
| 10 | `POWER_STATUS` | | słowo statusu zasilania (bity niżej) |

### Bity `POWER_STATUS` (adres 10)

| bit | nazwa | sygnał rejestru | uwaga |
|---:|---|---|---|
| 0 | MAINS_OK | `PWR.MAINS_OK` | wszystkie fazy obecne; `PWR.MAINS_LOST` = negacja |
| 1 | L1_OK | `PWR.L1_OK` | |
| 2 | L2_OK | `PWR.L2_OK` | |
| 3 | L3_OK | `PWR.L3_OK` | |
| 4 | NEUTRAL_OK | `PWR.NEUTRAL_OK` | |
| 5 | PHASE_SEQUENCE_OK | `PWR.PHASE_SEQUENCE_OK` | |
| 6 | BACKUP_AVAILABLE | `PWR.BACKUP_AVAILABLE` | |
| 7 | BACKUP_ACTIVE | `PWR.BACKUP_ACTIVE` | |
| 8 | DC_BUS_OK | `PWR.DC_BUS_OK` | |
| 9 | AUX_POWER_OK | `PWR.AUX_POWER_OK` | |
| 10 | POWER_24V_OK | `PWR.POWER_24V_OK` | `PWR.POWER_24V_FAULT` = negacja |

O tym, czy faza jest „obecna", decyduje EPM (jego próg i zwłoka) —
sterownik nie porównuje napięć z niczym.

## Blok diagnostyczny

EPM udostępnia także blok DIAG (adresy 500–504, komendy 600) — patrz
`CARD_DIAGNOSTIC_REGISTER_MAP.md`.

## Ten sam bit z dwóch źródeł

Sygnał `PWR.*` może też pochodzić ze styku na wejściu ELA z nadaną rolą
(etap 4 rejestru sygnałów). Projekt, w którym ten sam bit wystawia i EPM,
i rola punktu, dostaje ostrzeżenie w „Sprawdź projekt".
