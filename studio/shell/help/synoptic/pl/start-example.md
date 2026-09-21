# 2.4 Kompletny przyklad od zera

Kompletny przyklad: obwod od przylacza (punkt graniczny) przez szyne zbiorcza do dwoch odbiorow (dwoch stycznikow sterujacych oswietleniem). Krok po kroku, z konkretnymi wartosciami.

## Krok 1 - rejestry

1. Menu Aparaty > Rejestry projektu... > zakladka Lokalizacje: dodaj kod `MAG` (opis "Magazyn").
2. Zakladka Karty: dodaj karte `ELA1` (model dowolny, rodzaj DI, 16 kanalow) i karte `ADA1` (rodzaj DO, 16 kanalow).

## Krok 2 - dwa aparaty SWITCHED

1. Menu Aparaty > Lista aparatow... > + Dodaj. Id: lokalizacja `MAG`, sufiks `OSW1`. Oznaczenie `-K1`, nazwa "Oswietlenie regalu 1". Zachowanie SWITCHED, tryb sprzezenia DUAL, diClosed `ELA1.DI.1`, diOpen `ELA1.DI.2`. Sterowanie: 1 wyjscie, styl MAINTAINED, doClose `ADA1.DO.1`. Zapisz.
2. Powtorz dla drugiego odbioru: sufiks `OSW2`, oznaczenie `-K2`, diClosed `ELA1.DI.3`, diOpen `ELA1.DI.4`, doClose `ADA1.DO.2`.

## Krok 3 - ekran schematu

1. Przeciagnij z biblioteki symbol Boundary Point na plotno. We Properties ustaw Boundary Direction na SOURCE i Boundary Medium na ELECTRICAL.
2. Wybierz osrodek 1 (Electrical, klawisz `1`) i narysuj przewod ze stycznikiem punktu granicznego do miejsca, gdzie zacznie sie szyna.
3. Ustaw styl NOWEGO przewodu na Bus (przelacznik w gornym pasku narzedzi) i narysuj krotki, poziomy odcinek szyny.
4. Przeciagnij dwa symbole Circuit Breaker (albo Disconnect Switch) w poblize szyny. Narysuj po jednym przewodzie od kazdego z nich, konczac DOKLADNIE na dowolnym punkcie dlugosci szyny (nie tylko na jej koncu) - patrz [5.4](help://synoptic/sch-wire-style).
5. Zaznacz kazdy z dwoch symboli i we Properties, w polu Aparat, wybierz odpowiednio `MAG_OSW1` i `MAG_OSW2`.

Efekt: obie galezie licza sie do JEDNEJ sieci elektrycznej (bo stykaja sie geometrycznie z ta sama szyna - patrz [5.1](help://synoptic/sch-node-model)), a kazdy symbol pokazuje oznaczenie swojego aparatu (bo zostalo wypelnione automatycznie przy przypisaniu, patrz [6.4](help://synoptic/sym-device-binding)).
