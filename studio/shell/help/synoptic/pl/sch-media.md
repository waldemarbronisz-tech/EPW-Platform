# 5.3 Trzy osrodki: prad, woda, wentylacja

Kazdy przewod nalezy do jednego z trzech osrodkow: ELECTRICAL (prad), WATER (woda), VENTILATION (wentylacja). Wybor osrodka NOWEGO przewodu ustawia sie z gory (klawisze `1`/`2`/`3` albo przelacznik w toolbarze) - kazdy narysowany od tej pory przewod dziedziczy ten wybor, az do zmiany. Osrodek juz narysowanego przewodu mozna nadal zmienic pozniej we Properties.

Siec, ktora dotyka zaciskow z wiecej niz jednego osrodka naraz, jest bledem walidacji (`MIXED_MEDIUM` w `NetResolver.ts`) - dotyczy to kazdej pary z tych trzech, nie tylko prad-woda: prad spiety z wentylacja jest tak samo bledny jak prad spiety z woda.
