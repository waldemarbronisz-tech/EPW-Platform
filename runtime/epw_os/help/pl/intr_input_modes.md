# Tryby linii: stykowy vs. parametryzowany (EOL/DEOL)

Każda linia dozorowa ma dokładnie jeden z dwóch, wykluczających się
trybów wejścia, wybierany w oknie Konfiguruj linie (poziom Engineer):

**Stykowy (cyfrowy)** — domyślny, i tak działała każda linia przed
wprowadzeniem tej funkcji. Przypisany do wejścia cyfrowego i jego stanu
spoczynkowego, Normalnie zwarty albo Normalnie rozwarty — patrz
[Strefy i linie dozorowe](help://intr_zones_lines). Tylko dwa stany:
**Bezpieczna** albo **Naruszona**. Przecięty kabel wygląda dokładnie
tak samo jak spokojna czujka.

**Parametryzowany (analogowy)** — przypisany do punktu analogowego
zamiast wejścia cyfrowego, odczytywany jedną z dwóch metod:
- **EOL** (rezystor końca linii) — 3 stany: Bezpieczna, Naruszona,
  Przerwa.
- **DEOL** (podwójny rezystor końca linii) — 5 stanów: Bezpieczna,
  Naruszona, Sabotaż, Zwarcie, Przerwa.

Każdy stan ma własne, konfigurowalne **okno wartości** (od–do), w
którym musi się mieścić odczyt, żeby liczyć się za ten stan — ustawione
na sensowne wartości domyślne, ale zawsze do zmiany, bo faktyczne
wartości rezystorów zależą od okablowania w terenie i nigdy nie są
zaszyte na sztywno. Odczyt, który nie mieści się w *żadnym*
skonfigurowanym oknie, to **stan Nieokreślony** — traktowany dokładnie
jak awaria (poniżej), nigdy po cichu pomijany.

**Sabotaż, Zwarcie, Przerwa i Nieokreślony to zawsze AWARIA LINII** —
awaria alarmuje natychmiast, w każdym stanie strefy, dokładnie tak jak
robi to linia Całodobowa, niezależnie od tego, czy strefa jest
uzbrojona, **dla każdego typu linii bez wyjątku, także Dozorowej**.
Awaria to inny rodzaj zdarzenia niż zwykłe naruszenie — przecięty kabel
albo usunięty rezystor sabotażowy to sabotaż albo problem serwisowy na
każdej linii, a nie "ruch przed czujką" — patrz [Typy linii]
(help://intr_line_types), dlaczego własna zasada linii Dozorowej
"nigdy nie alarmuje" dotyczy konkretnie naruszenia, a nie awarii. Patrz
[Sygnały dla logiki](help://intr_tags) po tagi, które awaria wystawia.

**Lista wejść do wyboru pokazuje wyłącznie wejścia właściwego typu** —
tryb stykowy pokazuje tylko wejścia cyfrowe, tryb parametryzowany tylko
punkty analogowe; przypisanie złego typu z tego okna nie jest możliwe.
Zmiana trybu linii czyści dotychczas wybrane wejście (najpierw pojawia
się ostrzeżenie) — stare przypisanie nie przechodzi po cichu dalej,
skoro może już w ogóle nie mieć sensu w nowym trybie.
