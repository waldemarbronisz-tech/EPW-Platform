# 5.7 Punkt graniczny: zrodlo i odplyw instalacji

Punkt graniczny reprezentuje miejsce, w ktorym instalacja na tym ekranie laczy sie ze swiatem zewnetrznym: przylacze energetyczne, studnia, punkt zrzutu. To jedyny symbol z polem kierunku: Boundary Direction, SOURCE (zrodlo) albo SINK (odplyw), plus Boundary Medium (ELECTRICAL/WATER/VENTILATION).

Dwa punkty graniczne SOURCE spiete w jedna siec sa ostrzezeniem (`MULTIPLE_SOURCES`, [5.6](help://synoptic/sch-net-validation)) - dwa niezalezne zasilania podpiete razem to realny problem instalacyjny (np. rownolegla praca dwoch zrodel bez synchronizacji), ktory warto zauwazyc juz na etapie projektowania ekranu.

Etykieta i podetykieta punktu granicznego to designation/description tego obiektu (nie osobne pola), a jego jedyny zacisk lezy po stronie wskazanej polem Boundary Port Side (gora/dol/lewo/prawo) - w przeciwienstwie do kazdego innego symbolu, ktorego zaciski maja stale pozycje z rejestru ([6.2](help://synoptic/sym-terminals)), ten jeden ma pozycje zacisku wybierana per instancja.
