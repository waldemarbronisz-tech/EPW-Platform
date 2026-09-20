# Co ten panel może zmienić w projekcie

Nie wszystko w `projekt.epw` jest równe. Ten podział decyduje, co wolno
poprawić przy szafie, a co musi wrócić przez Studio.

## Nastawa — tak

Wartość czegoś, co już istnieje: czasy na wejście i wyjście strefy,
filtry linii dozorowej, progi zabezpieczenia, skalowanie punktu
analogowego, ustawienia MQTT, czas sygnalizacji syreny.

Zmiana takiej wartości tutaj zapisuje ją **do pliku projektu**, podnosi
rewizję i odnotowuje w dzienniku, że przyszła z panelu. Studio widzi
potem różnicę i może ją przyjąć — więc poprawka zrobiona o trzeciej
w nocy nie przepada przy następnej wysyłce z laptopa.

## Struktura — nie

To, co w ogóle istnieje: karty, punkty, aparaty, skład urządzenia,
strefy, linie, ekrany, logika. Ten panel **odmawia** takiej zmiany
i zapisuje odmowę w dzienniku.

To nie jest ograniczenie do obejścia. Sterownik, którego skład może się
rozjechać przy szafie, to sterownik, którego rysunek przestaje go
opisywać.

## Rewizja

Każdy zapis ją podnosi i odnotowuje, kto zapisał: Studio czy panel. To
dzięki niej [wgranie projektu](help://proj_install) potrafi rozpoznać,
że ten sterownik ma coś nowszego niż laptop — i zatrzymać się zamiast
nadpisać czyjąś pracę.

## Czego w projekcie nie ma nigdy

PIN-ów, kodów użytkowników alarmówki, tokenów zdalnych i hasła do
brokera MQTT. To należy do **tego egzemplarza sterownika**, nie do
instalacji, i leży w jego własnych plikach lokalnych, zapisane
jednokierunkowo. Projekt jedzie do Studia, do repozytorium i po sieci;
sekrety nie jadą.
