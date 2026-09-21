# 1.1 Czym jest EPW-Synoptic-Editor

EPW-Synoptic-Editor tworzy i waliduje pliki projektu dla ekranu schematu elektrycznego/wodnego/wentylacyjnego: symbole, przewody, mierniki, panele sygnalizacyjne. To narzedzie EDYCYJNE - dziala offline, na pliku na dysku, i nie ma pojecia o zadnym zywym stanie instalacji.

Edytor NIE wykonuje logiki sterowania, NIE odpytuje sterownikow po Modbusie ani zadnym innym protokole, i NIE wie, czy stycznik jest aktualnie zalaczony. Wszystko, co widac na ekranie podczas edycji - stan diody, wartosc na mierniku - to podglad ustawiony recznie w polu `Editor Preview`, nie odczyt z prawdziwego urzadzenia.

Efektem pracy w tym edytorze jest plik projektu (rozszerzenie `.epwsyn`) zawierajacy geometrie ekranu i liste aparatow. Ten plik dopiero PRZEZNACZONY jest do uruchomienia w [EPW-OS](help://synoptic/intro-platform) - zobacz rozdzial 10 po szczegoly, co dzis faktycznie dziala na tej sciezce.

> **Uwaga:** Zasada, ktora wraca w kazdym rozdziale tej pomocy: jesli czegos nie widac wprost w programie albo w pliku projektu, to tego nie ma. Ten tekst opisuje kod takim, jaki jest.
