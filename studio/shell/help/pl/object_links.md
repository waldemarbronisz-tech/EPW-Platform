# Powiązania obiektu

Punkt jednego sterownika, dostępny u drugiego. Przez MQTT: źródło
publikuje swoje tagi, cel je subskrybuje.

Potrzebny jest zapisany [obiekt z co najmniej dwoma
sterownikami](help://site).

| Kolumna | Znaczenie |
|---|---|
| **Źródło** | sterownik, który ma tę wartość |
| **Punkt źródłowy** | jego punkt |
| **Cel** | sterownik, który ma ją widzieć |
| **Tag `Link.*` na celu** | jak się będzie nazywać u celu: `Link.<Id>.In<nazwa>` |
| **Typ** | typ wartości |
| **Nieaktualna po** | po jakim czasie bez odświeżenia uznać ją za nieaktualną |

## Co Studio robi za Ciebie

Wpisuje mapowanie przychodzące do [MQTT](help://mqtt) sterownika
docelowego, a jeśli trzeba — włącza tam MQTT i nadaje prefiks tematów.
Usunięcie sterownika z obiektu zabiera jego powiązania.

Mapowań wpisanych ręcznie Studio **nigdy nie rusza**.

## Czym `Link.*` jest, a czym nie

Tag `Link.*` działa w [logice](help://logic) i na
[ekranach](help://screens) celu jak każdy inny tag — ale jest
**wyłącznie wartością do odczytu**. Nigdy nie jest komendą: nie da się
przez to sterować aparatem drugiego sterownika.

Nie ma też adresowania między projektami na ekranach — ekran celu wiąże
symbol z tagiem `Link.*` tak jak z każdym innym.
