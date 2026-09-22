# Rola punktu — styki z obcych urządzeń (rejestr sygnałów, etap 4)

Część sygnałów rejestru nie przychodzi po Modbus, tylko **stykiem na
wejście ELA**: zadziałanie zewnętrznego przekaźnika zabezpieczeniowego
(np. e²TANGO na polu SN), styki stanu UPS, przekaźnik kontroli 24 V,
przekaźnik obecności sieci. Rejestr punktów w Studiu daje punktowi DI
**rolę** (który sygnał rejestru niesie ten styk) i **typ styku** (NO/NC),
a sterownik wystawia bit pod tą samą nazwą, którą dałby mu EPM albo
ADA01. Logika nie wie i nie musi wiedzieć, skąd bit przyszedł.

Kod: lista ról `shared/logic/point_roles.py`, źródło w sterowniku
`runtime/epw_os/core/point_role_signals.py`, kolumny „Rola” i „Styk”
w `studio/shell/project_panels.py` (`PointRegistryPanel`), kontrola
w „Sprawdź projekt” (`validate_project`, punkt 9).

## Lista ról

Rolą może być **tylko sygnał z katalogu** z grup PWR, UPS i PROT, który
jeden styk jest w stanie nieść. Poza listą (celowo):

| pominięte | dlaczego |
|---|---|
| `PROT.<stopień>.*` | słowo stopnia daje tylko ADA01 |
| `PWR.MAINS_LOST`, `PWR.POWER_24V_FAULT` | sterownik wylicza je jako negację `PWR.MAINS_OK` / `PWR.POWER_24V_OK` — nadaj rolę „OK” i dobierz typ styku |
| `PROT.SETTINGS_MISMATCH`, `PROT.TEST_ACTIVE`, `PROT.TEST_OK` | porównanie sum kontrolnych i autotest firmware ADA01, nie styk |

Wynik: 11 ról PWR, 8 ról UPS, 16 ról PROT (bity zbiorcze i stan).

## Polaryzacja (typ styku)

Zasada platformy: **sygnał nadzoru TRUE = stan sprawny.** Styk NO
przekaźnika *zamyka się*, gdy warunek zachodzi; styk NC *otwiera się*.

| typ styku | bit rejestru |
|---|---|
| NO | = wejście DI (zamknięty = TRUE) |
| NC | = negacja wejścia DI (otwarty = TRUE) |

Rola `PWR.MAINS_OK` na styku NC przekaźnika sieci: wejście otwarte
(przekaźnik zasilony) → bit TRUE. Rola `UPS.ON_BATTERY` na styku NO:
styk zamknięty → bit TRUE.

## Brak danych (zasada Z4)

Gdy jakość tagu wejścia nie jest GOOD (karta nie odpowiada, wejście
jeszcze nie odczytane, wymuszona zła jakość), bit przyjmuje **wartość
bezpieczną z katalogu** (`UPS.FAULT` = TRUE, `PWR.MAINS_LOST` = TRUE,
`PROT.FAIL` = TRUE, reszta FALSE), a `COMM.<karta>.ONLINE = FALSE` mówi
dlaczego. `UPS.*` bez żadnego punktu z rolą czyta się tak samo — jak
`PWR.*` bez EPM.

## Dwa źródła jednego bitu

Ten sam bit może wystawiać i blok rejestrów urządzenia (PWR — EPM,
PROT — ADA01), i rola punktu. **W sterowniku wygrywa rola punktu**
(`PointRoleSignals` jest pytany przed `DeviceSignals`) i mówi o tym raz
w logu. „Sprawdź projekt” pokazuje ostrzeżenie *dwa źródła jednego bitu*
oraz ostrzeżenie, gdy jedną rolę niesie więcej punktów (wtedy bit typu
„sprawny” wymaga wszystkich styków, bit typu „zdarzenie” — dowolnego;
tabela `HEALTHY_TRUE` w `point_roles.py`).
