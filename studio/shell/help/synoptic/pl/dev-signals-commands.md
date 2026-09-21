# 4.9 Sygnaly i komendy udostepniane logice sterowania

Kazdy aparat udostepnia logice sterowania w EPW-Logic-Studio zestaw sygnalow, komend i - dla niektorych zachowan - sygnalow zakazu (INHIBIT), wyliczany WYLACZNIE z pola behavior (nigdy osobno deklarowany).

| Zachowanie | Sygnaly (odczyt) | Komendy (zapis) |
| --- | --- | --- |
| SWITCHED | stan (otwarty/zamkniety/w ruchu/blad), rozbieznosc, .COUNTER (jesli wlaczony) | OTWORZ / ZAMKNIJ |
| SIGNAL | stan alarmowy | (brak) |
| MEASURED | wartosc pomiaru | (brak) |
| MODULATED | wartosc zadana, wartosc zwrotna (jesli skonfigurowana) | ustaw wartosc |

Sygnaly zakazu (INHIBIT) istnieja po to, zeby logika mogla ZABRONIC wykonania polecenia, nie tylko je wyslac. Bez nich logika sterowania umie ZALACZYC aparat, ale nie umie go ZABLOKOWAC przed poleceniem, ktore operator wysyla wprost z ekranu - polecenie operatora idzie wtedy prosto na wyjscie, bez mozliwosci przechwycenia go przez blokade logiki.
