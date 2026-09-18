# Notatki serwisowe

Dziennik serwisowy aparatów: wpisy „co zrobiono” (wymiana zestawu
styków, widoczne wżery), pisane ręcznie na panelu sterownika przez
Operatora lub wyżej. Uzupełniają liczniki łączeń, które mówią „ile
razy / jak długo”.

**Wpisy są nieusuwalne i nieedytowalne** - to dziennik, nie notatnik;
pomyłkę poprawia się kolejnym wpisem. Studio tylko je pokazuje.

Od 2026-09-18 notatki są częścią projektu: każdy wpis dodany na panelu
zapisuje się do `projekt.epw` (rewizja +1 „panel”), więc historia
instalacji jedzie z projektem. Do Studio trafiają przez „Zgraj z
urządzenia” albo „Przyjmij nastawy ze sterownika” (Sterownik → Nastawy
sterownika na żywo pokazuje je jako różnicę `service_notes/<aparat>/notes`).

Uwaga: wysłanie projektu, który ma mniej wpisów niż sterownik, nadpisze
jego dziennik - panel Sterownik pokaże tę różnicę przed wysłaniem.
