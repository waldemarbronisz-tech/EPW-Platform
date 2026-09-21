# 10.1 Co zawiera plik projektu

Plik projektu (`.epwsyn`, JSON) ma pole `format: "EPW_SYNOPTIC"` i `schema_version`. Zawiera: metadane projektu, konfiguracje kanwy, tablice `objects` i `connections`, opcjonalnie `meters`, `signalPanels`, `frames`, `devices`, `locations`, `cards`, `kind` (rodzaj ekranu - dzis zawsze SCHEMATIC, patrz [1.4](help://synoptic/intro-screens)) i `helpLanguage` (jezyk pomocy).

Kazde z pol opcjonalnych zostalo dodane w ten sam sposob: dopisane jako nowe pole bez podnoszenia numeru wersji schematu, bo starszy plik po prostu nie ma tego pola i wczytuje sie z sensowna wartoscia domyslna (pusta tablica/mapa, jezyk polski) zamiast bledu.

> **Uwaga:** W repozytorium istnieje TAKZE drugi, niezalezny format o nazwie EPW_PROJECT (plik `ProjectV2Schema.ts`), z zupelnie innym modelem (wiele ekranow w jednym pliku, polaczenia oparte na portach zamiast na wezlach). Nic w dzialajacym edytorze go dzis nie zapisuje ani nie odczytuje - to wylacznie definicje typow i walidator, przygotowanie pod przyszla architekture, nie aktywny format.
