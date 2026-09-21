# 1.4 Rodzaj ekranu i pole kind

Kazdy projekt to ekran SCHEMATIC: symbole, przewody, mierniki, panele sygnalizacyjne (rozdzial [5](help://synoptic/sch-node-model)). Zapisywany jest w pliku jako pole `kind`, ale SCHEMATIC to dzis jedyna wartosc, jaka to pole moze mieć w NOWO zapisanym pliku.

Wczesniejsza wersja tego edytora miala tez drugi rodzaj ekranu, PLAN (rzut izometryczny dzialki, wlasna kanwa, wlasna biblioteka obiektow na kaflach) - zostal on calkowicie usuniety. Pole `kind` zostalo w formacie pliku wylacznie po to, zeby STARY plik zapisany z `kind: "PLAN"` wciaz dalo sie otworzyc: taki plik wczytuje sie normalnie, jego ekran jest cicho konwertowany na SCHEMATIC, a w panelu Messages pojawia sie o tym informacja - plik NIE jest odrzucany, a numer wersji schematu (`schema_version`) sie nie zmienia.

Plik bez pola `kind` w ogole (kazdy plik zapisany, zanim ten koncept powstal) wczytuje sie jako SCHEMATIC bez zadnego komunikatu - to byl, i nadal jest, jedyny sensowny domyslny rodzaj ekranu.
