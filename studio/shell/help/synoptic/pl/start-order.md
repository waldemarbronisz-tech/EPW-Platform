# 2.2 Kolejnosc pracy: najpierw rejestry, potem aparaty, potem ekran

Praktyczna kolejnosc pracy nad nowym projektem SCHEMATIC to: NAJPIERW rejestry (lokalizacje i karty, rozdzial 3), POTEM aparaty (rozdzial 4), a DOPIERO POTEM symbole na ekranie (rozdzial 6).

Powod jest wprost w kontrakcie danych: identyfikator aparatu MUSI zaczynac sie kodem juz istniejacej lokalizacji (`validateDeviceId` w `DeviceValidation.ts`), a kazdy adres kanalu MUSI wskazywac na juz istniejaca karte (`validateChannelAddress`). Formularz aparatu wymusza to bezposrednio: przy tworzeniu nowego aparatu pole Id to rozwijana lista lokalizacji, nie wolny tekst - jesli lista jest pusta, dodanie aparatu jest zablokowane z podpowiedzia "Najpierw dodaj lokalizacje w Rejestrach projektu".

Symbol na ekranie schematu nie tworzy aparatu - tylko wskazuje na juz istniejacy przez rozwijana liste Aparat we Properties ([6.4](help://synoptic/sym-device-binding)). Umieszczenie symbolu przed dodaniem aparatow po prostu zostawia go bez przypisania (co jest poprawnym stanem - patrz [4.1](help://synoptic/dev-why-not-in-screen)) do czasu, az aparat powstanie.
