# 2.3 Zapis i otwarcie projektu

`File > Save` i `Save As...` zapisuja caly stan projektu do jednego pliku `.epwsyn` (format JSON, pole `format: "EPW_SYNOPTIC"`) przez natywny mechanizm zapisu pliku przegladarki. `File > Open...` czyta taki plik z powrotem.

Zapisywane jest wszystko: metadane projektu, konfiguracja kanwy, obiekty i przewody, mierniki i panele sygnalizacyjne, ramki, lokalizacje/karty/aparaty, rodzaj ekranu oraz wybrany jezyk pomocy. Szczegoly zawartosci pliku sa w [10.1](help://synoptic/file-contents).

Wczytanie pliku ze zbyt nowa wersja schematu (pole `schema_version` wieksze niz obslugiwana) jest odrzucane z komunikatem bledu zamiast czesciowego, nieprzewidywalnego wczytania - zobacz [10.2](help://synoptic/file-versioning).
