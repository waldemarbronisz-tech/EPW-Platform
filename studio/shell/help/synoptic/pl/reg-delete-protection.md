# 3.4 Dlaczego usuniecie uzywanej lokalizacji albo karty jest zablokowane

Usuniecie lokalizacji, ktorej kod jest przedrostkiem identyfikatora choc jednego istniejacego aparatu, jest zablokowane - przycisk Usun jest wygaszony, a najechanie na niego pokazuje liczbe aparatow, ktore go uzywaja.

Podobnie usuniecie karty, ktorej choc jeden kanal jest wpisany w adres jakiegokolwiek aparatu, jest zablokowane - z tego samego powodu: usuniecie karty zostawiloby te aparaty z adresami wskazujacymi na nieistniejaca karte.

To nie jest ograniczenie interfejsu dodane "na wszelki wypadek" - to bezposrednia konsekwencja tego, jak identyfikator aparatu i adres kanalu sa zbudowane (patrz [3.1](help://synoptic/reg-locations) i [3.3](help://synoptic/reg-addressing)): usuniecie uzywanej lokalizacji lub karty zostawiloby dane w stanie, ktorego `validateDeviceRegistry` nie potrafiloby juz uznac za poprawny.
