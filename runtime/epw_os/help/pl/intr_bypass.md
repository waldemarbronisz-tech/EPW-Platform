# Wyłączanie linii (bypass)

Linię można tymczasowo wyłączyć ze sprawdzania przy uzbrajaniu/
alarmowaniu — przycisk **Bypass** obok niej na stronie Podgląd
(poziom Engineer). W trakcie bypassu stan naruszenia tej linii zawsze
odczytywany jest jako bezpieczny przez resztę systemu (zarówno
uzbrajanie, jak i alarmowanie całkowicie ją pomijają), niezależnie od
tego, co faktycznie zgłasza czujka.

Używaj tego dla czujki, o której wiesz, że jest uszkodzona albo celowo
zostawiona otwarta, bez konieczności usuwania i ponownego dodawania
całej jej konfiguracji.

Każdy bypass — włączenie i wyłączenie — trafia do dziennika audytowego:
kto, kiedy, która linia. Bypass **nie przetrwa restartu**: program
zawsze wstaje z niczym niewyłączonym, więc czujka nigdy nie może zostać
po cichu zapomniana jako wyłączona po restarcie.

Wyłączenie linii bypassem nie czyści alarmu już przez nią wywołanego —
do tego służy rozbrojenie strefy (patrz
[Uzbrajanie, rozbrajanie i czasy](help://intr_arming)).
