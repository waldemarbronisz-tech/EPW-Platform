# Dozór nocny (uzbrojenie częściowe)

Uzbrojenie strefy **w pełni** dozoruje każdą jej linię. Uzbrojenie jej
**nocą** dozoruje tylko linie oznaczone jako czuwające nocą — dzięki
czemu ludzie mogą chodzić wewnątrz budynku, którego perymetr nadal jest
pilnowany.

## Gdzie są te dwa przyciski

Na stronie Przegląd strefa ma **Uzbrój**, a obok **Uzbrój (noc)** — ale
tylko wtedy, gdy dozór nocny faktycznie chroniłby coś innego. Strefa,
której każda linia czuwa nocą, jest chroniona tak samo w obu trybach,
więc nie ma między czym wybierać i pojawia się jeden przycisk.

## Które linie czuwają dalej

Każda linia dozorowa ma flagę **Czuwa nocą**, ustawianą w Studiu.
Odznaczona to zwykły wybór dla czujek ruchu wewnątrz.

Dwa typy linii ignorują tę flagę zupełnie i alarmują tak czy inaczej:

- **Całodobowa** — styk sabotażowy nie interesuje się tym, jak strefa
  jest uzbrojona ani czy w ogóle;
- **Napadowa** — przycisk napadowy działający tylko przy uzbrojonym
  obiekcie byłby gorszy niż żaden.

**Awaria linii** (sabotaż, zwarcie, przerwany przewód) również alarmuje
niezależnie, na każdym typie linii.

## Linia wykluczona nocą nie blokuje uzbrojenia

Odmowa uzbrojenia nocnego dlatego, że czujka ruchu w holu widzi osobę,
która właśnie uzbraja, czyniłaby cały tryb bezużytecznym. Sprawdzane są
tylko te linie, które nocą naprawdę czuwają.

## Co strefa pokazuje potem

Wiersz strefy mówi, w jakim trybie jest uzbrojona, żeby „uzbrojona"
nigdy nie zacierało różnicy między całym budynkiem a jego perymetrem.

Rozbrojenie zawsze przywraca uzbrajanie pełne na następny raz: strefa
uzbrojona nocą nie może po cichu uzbroić się nocą znowu, gdy ktoś
naciśnie zwykłe **Uzbrój**.

## W logice

`SEC.SYSTEM.ARMED` wymaga uzbrojenia **pełnego** wszystkich stref.
`SEC.SYSTEM.ARMED_PARTIAL` obejmuje i „część stref uzbrojona", i „uzbrojona,
ale nocą". `REQ.SEC.ARM_ALL_PARTIAL` uzbraja nocą wszystkie strefy. Patrz
[Co widzi program logiki](help://logic_signals).
