# Sprawdź projekt

Szuka rozjazdów, których nie widać w żadnej pojedynczej tabeli, bo
dotyczą **dwóch działów naraz**. Dwuklik na wpisie przenosi prosto do
miejsca problemu.

Podsumowanie rozdziela **Błędy** i **Ostrzeżenia**.

## Co sprawdza

| Wpis | Co to znaczy |
|---|---|
| aparat wskazuje punkt, którego nie ma w rejestrze | punkt został skasowany albo adres jest literówką |
| aparat wskazuje punkt na karcie, której już nie ma w składzie | karta zniknęła, przypisanie zostało |
| **punkt przypisany do więcej niż jednego aparatu** | dwa aparaty sterowałyby tym samym wyjściem |
| punkt wskazuje lokalizację spoza listy | lokalizacja została usunięta albo przemianowana |
| linia dozorowa wskazuje punkt, którego nie ma | linia nie ma czego pilnować |
| zabezpieczenie procesowe wskazuje punkt, którego nie ma | jak wyżej |
| zabezpieczenie procesowe wskazuje punkt **nie-AI** | progi wymagają wartości analogowej |
| moduł ma dane, ale jest poza składem | **ostrzeżenie**: gałąź ukryta, dane nietknięte |
| styl impulsowy z czasem impulsu 0 ms | impuls o zerowej długości nic nie zrobi |
| `PULSE_TOGGLE` bez potwierdzenia | każdy impuls przerzuca, więc stan musi być znany |
| `PULSE_TOGGLE` z więcej niż dwoma wyjściami | ten styl obsługuje jedno albo dwa |

## Kiedy to robić

Przed każdą wysyłką na sterownik. Sterownik przyjmie projekt, który nie
przeszedł tego sprawdzenia — format jest poprawny, więc nie ma podstaw,
żeby odmówić — ale aparat wskazujący nieistniejący punkt po prostu nie
zadziała, i dowiesz się o tym przy szafie, a nie przy biurku.
