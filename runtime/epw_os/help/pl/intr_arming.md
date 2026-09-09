# Uzbrajanie, rozbrajanie i czasy na wejście/wyjście

Uzbrojenie i rozbrojenie strefy wymaga **poziomu Operator lub
wyższego**, ze strony System alarmowy (albo z logiki — patrz
[Sygnały dla logiki](help://intr_tags)).

Stany strefy:

- **ROZBROJONA** — nie nadzoruje (poza ewentualną linią Całodobową,
  która nadzoruje zawsze).
- **ODLICZANIE WYJŚCIA** — uzbrojenie właśnie zażądane, strefa ma
  skonfigurowany czas na wyjście; odlicza, potem przechodzi w
  UZBROJONA. Daje czas na opuszczenie obiektu bez wywołania alarmu.
- **UZBROJONA** — aktywnie nadzoruje każdą linię w strefie.
- **ODLICZANIE WEJŚCIA** — linia typu Zwłoczna została naruszona przy
  UZBROJONEJ strefie; odlicza, dając czas na rozbrojenie zanim
  przejdzie w ALARM.
- **ALARM** — naruszenie, którego bieżący stan strefy nie usprawiedliwiał.
  Rozbrojenie strefy (Operator+) zawsze je czyści, z każdego stanu.

**Jeśli w chwili próby uzbrojenia jakaś linia jest już naruszona**,
program informuje, która to, i nie uzbraja po cichu — trzeba jawnie
potwierdzić uzbrojenie mimo to. Nie może się to zdarzyć przez
przypadek.

**To samo dotyczy linii w awarii** (sabotaż, zwarcie, przerwa albo stan
nieokreślony — patrz
[Tryby linii](help://intr_input_modes)): uzbrojenie wymaga takiego
samego jawnego potwierdzenia, ze wskazaniem której linii dotyczy i że
to awaria, a nie zwykłe naruszenie. Uzbrojenie nadal jest możliwe —
potwierdzenie ma tylko zapewnić, że nie stanie się to nieświadomie — a
taka decyzja trafia do dziennika audytowego osobno, jako uzbrojenie
*mimo* awarii.

Pozostałe sekundy odliczania widać na stronie Podgląd dla
każdej strefy w stanie ODLICZANIE WYJŚCIA/WEJŚCIA, a zbiorczy stan
systemu zawsze widać na pasku statusu.
