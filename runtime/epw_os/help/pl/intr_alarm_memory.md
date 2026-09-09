# Pierwsza przyczyna i pamięć alarmu

Gdy strefa zaalarmuje, system zapamiętuje dokładnie, która linia
wywołała go jako pierwsza, i utrzymuje ten zapis widoczny, dopóki ktoś
go nie skasuje — nawet po rozbrojeniu strefy.

**Pierwsza przyczyna** — linia i dokładny czas, które rozpoczęły bieżący
alarm. Jeśli kilka linii naruszy się jedna po drugiej (ktoś idzie przez
obiekt), każda kolejna też zostaje zapisana, ale wyraźnie osobno — jako
*kolejne alarmy*, nigdy zlane w jedną listę z pierwszą przyczyną. To
właśnie ta informacja pokazuje, którędy ktoś faktycznie wszedł.

**Pamięć alarmu** — gdy strefa raz zaalarmuje, jej pamięć pozostaje
**aktywna**, dopóki nie zostanie jawnie skasowana, niezależnie od tego,
co dzieje się ze strefą w międzyczasie: rozbrojenie, ponowne uzbrojenie,
a nawet pełny restart programu. To ta sama zasada, którą w tym programie
stosuje już zatrzask w safety_kernel — zdarzenie, które się wydarzyło,
zostaje na zapisie; nie znika po cichu tylko dlatego, że bezpośrednie
zagrożenie minęło. Wiersz strefy pokazuje dopisek "pamięć alarmu",
dopóki jest aktywna, a przycisk **Pamięć alarmu** (na pasku narzędzi,
nad listą stref) otwiera pełny obraz dla dowolnej strefy: czy jest
aktywna, pierwszą przyczynę z linią i czasem, oraz listę wszystkiego,
co zaalarmowało później.

**Kasowanie** — poziom Operator lub wyższy, przyciskiem Skasuj w oknie
Pamięci alarmu. Skasowanie trafia do dziennika audytowego oraz do
[historii zdarzeń alarmowych](help://intr_history). Po skasowaniu
kolejny alarm (kiedykolwiek nastąpi) rozpoczyna zupełnie nowy zapis —
własną pierwszą przyczynę, własną listę.

Nic w sposobie uzbrajania, rozbrajania ani przechodzenia strefy w stan
ALARM się nie zmienia — patrz
[Uzbrajanie, rozbrajanie i czasy](help://intr_arming). To dotyczy
wyłącznie tego, co zostaje *zapamiętane* o alarmie, który już się
wydarzył.
