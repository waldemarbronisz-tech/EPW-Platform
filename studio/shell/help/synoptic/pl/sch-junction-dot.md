# 5.5 Kropka wezlowa - kiedy sie pojawia

Kropka wezlowa pojawia sie w kazdym punkcie siatki, w ktorym spotykaja sie TRZY LUB WIECEJ galezi - trzy lub wiecej odcinkow przewodow, albo dwa odcinki i zacisk symbolu (`getJunctionPoints` w `NetResolver.ts`).

Zwykle zagiecie tego samego przewodu (dwa jego wlasne odcinki spotykajace sie w jednym punkcie) NIE jest junction - to tylko naroznik, liczy sie jako dwie galezie, nie trzy. Punkt w SRODKU dlugosci jednego odcinka (np. odczep od szyny - [5.4](help://synoptic/sch-wire-style)) liczy sie jako DWIE galezie tego jednego odcinka (bo dzieli go koncepcyjnie na dwa), wiec odczep + ten punkt srodkowy dają razem trzy - i tam kropka sie pojawia.
