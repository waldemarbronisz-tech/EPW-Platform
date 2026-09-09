# shared/ — część wspólna platformy

Dokumenty opisujące **kontrakty między programami**. Zmiana czegokolwiek
tutaj dotyczy wszystkich trzech części platformy i wymaga uzgodnienia.

| Plik | Co opisuje |
|---|---|
| `SPEC_FORMAT_EPW.md` | Projekt formatu `.epw` — jeden plik na cały projekt |
| `RUNTIME_CONTRACT.md` | Kontrakt między edytorem ekranów a runtime'em |
| `REJESTR_UZUPELNIENIE.md` | Pełna lista sygnałów wystawianych przez runtime |
| `PL_TERMINOLOGIA_DO_PRZEGLADU.md` | Terminologia polska do ujednolicenia |

## Obowiązujący format ekranów

`.epwsyn`, nazwa formatu `EPW_SYNOPTIC`, wersja schematu **2**.

Definicja: `studio/synoptic/src/project/ProjectSchema.ts`

⚠️ W repozytorium edytora istnieje także `ProjectV2Schema.ts` z formatem
`EPW_PROJECT`. **To nie jest format docelowy** — nieużywany szkic,
którego żaden kod nie zapisuje ani nie czyta. Do przemianowania, żeby
przestał mylić.

## Rejestr aparatów

Zapisywany w polu `devices` wewnątrz `.epwsyn`.
Definicja: `studio/synoptic/src/project/DeviceSchema.ts`

Zasada: **konfiguracja aparatu nie mieszka na ekranie.** Ekran mówi
tylko „w tym miejscu, tym symbolem, pokaż aparat o tym identyfikatorze".

Pięć zachowań: `SWITCHED`, `SIGNAL`, `MEASURED`, `MODULATED`, `SELECTOR`.

## Konwencja nazw sygnałów

Pełne słowa, nie skróty: `Security.` `Safety.` `System.` `Process.`
`Device.` `Cabinet.` `Meas.` `Sim.` `Marker.` `Link.` `Request.`

Szczegóły w zewnętrznym arkuszu `EPW_Rejestr_Bitow_Wewnetrznych`.
