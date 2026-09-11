# Karty wejść/wyjść

Rejestr fizycznych modułów wejść/wyjść: ELA (cyfrowe), ADA (analogowe/
zabezpieczenia), EPM i podobne. Dla każdego modułu:

- **Id** — adres logiczny nadany przez Ciebie (np. `ELA1`) — to on
  tworzy prefiks adresów punktów (`ELA1.DI.1`, `ELA1.DI.2`, ...).
- **Model** — opis/oznaczenie fizyczne (np. `ELA01`).
- **Rodzaj** — DI / DO / AI / AO — jaki typ kanałów ma ten moduł.
- **Kanały** — ile kanałów tego rodzaju moduł udostępnia.
- **Adres Modbus** — numer urządzenia (unit id, 1–247) na magistrali
  Modbus, którą sterownik (Orange Pi) rozmawia z modułami.

**Dodanie karty automatycznie tworzy jej punkty** w Rejestrze punktów —
nie wpisujesz ich ręcznie. Zmiana rodzaju/liczby kanałów przelicza je
na nowo, zachowując opisy już wpisane.

Na dole panelu: **Magistrala Modbus** — jedna, wspólna dla wszystkich
modułów: RTU (port szeregowy, prędkość, parzystość) albo TCP (adres
bramki, port). To ustawienie, jak sterownik ma w ogóle mówić z
modułami — dziś zapisywane w projekcie, gotowe na przyszły sterownik
Modbus w runtime (jeszcze nie zaimplementowany).
