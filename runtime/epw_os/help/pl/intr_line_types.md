# Typy linii

Każda linia dozorowa ma dokładnie jeden z czterech typów, wybierany przy
konfiguracji:

- **Natychmiastowa** — wywołuje alarm w chwili naruszenia, ale tylko
  gdy strefa jest UZBROJONA. Brak efektu przy rozbrojonej strefie albo
  w trakcie odliczania wejścia/wyjścia.
- **Zwłoczna** — typ wejście/wyjście. Naruszenie przy UZBROJONEJ strefie
  uruchamia odliczanie wejścia zamiast natychmiastowego alarmu; jeśli
  strefa nie zostanie rozbrojona zanim odliczanie dojdzie do zera,
  następuje alarm. Brak efektu przy już rozbrojonej strefie.
- **Całodobowa** — alarmuje natychmiast **niezależnie od stanu
  uzbrojenia strefy**, także przy całkowicie rozbrojonej. Dla rzeczy,
  które nigdy nie powinny być naruszone — styk sabotażowy, chroniona
  szafka.
- **Dozorowa** — sygnalizuje swoje naruszenie (widoczne na stronie i dla
  logiki — patrz [Sygnały dla logiki](help://intr_tags)), ale **nigdy**
  nie wywołuje alarmu przy naruszeniu, w żadnym stanie strefy. Dla czujek
  zewnętrznych, które chcesz obserwować lub na które chcesz reagować
  (np. sterowanie oświetleniem) bez czynienia ich częścią alarmu. Dotyczy
  to wyłącznie *naruszenia* (ruch przed czujką) — *awaria* tej samej
  linii (sabotaż, zwarcie, przerwa) nadal alarmuje dokładnie tak samo,
  jak każdy inny typ linii; patrz
  [Tryby pracy: stykowy i parametryzowany](help://intr_input_modes),
  co liczy się jako awaria.

Czas na wyjście i czas na wejście danej strefy (patrz
[Uzbrajanie, rozbrajanie i czasy](help://intr_arming)) dotyczą każdej
linii typu Natychmiastowa/Zwłoczna w tej strefie jako całości — w
trakcie odliczania te dwa typy linii są nieaktywne; tylko linia
Całodobowa przebija się przez to w każdym stanie.
