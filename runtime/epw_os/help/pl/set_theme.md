# Motywy wizualne

**Ustawienia → Motyw...** wybiera paletę kolorów programu. Pięć
wbudowanych motywów: **Industrial** (oryginalny wygląd programu i
ustawienie domyślne), **Night** (ciemne tło), **High Contrast**
(czytelność w pełnym słońcu, np. szafka zewnętrzna), **Cyberpunk**
(neonowe akcenty) oraz **SimCity 2000** (ciepła, retro paleta). Motyw
zmienia wyłącznie kolory — kształty, układ i zawartość każdego okna
pozostają dokładnie takie same, a zmiana działa natychmiast, bez
potrzeby restartu.

## Tryb pracy: stały, albo automatyczny dzień/noc

Własny wybór **trybu pracy** w oknie decyduje, jak wybierany jest
aktywny motyw:

- **Motyw stały** (domyślny) — wybierz jeden motyw, obowiązuje zawsze,
  dokładnie jak w każdej wcześniejszej wersji tego programu. Wybór
  innego motywu tutaj jest dostępny na **każdym poziomie dostępu, bez
  PIN-u** — to preferencja wyświetlania, nie zabezpieczenie, ta sama
  zasada co przy Języku czy Wygaszaniu ekranu.
- **Automatyczny dzień/noc** — wybierz motyw dzienny, motyw nocny oraz
  dwie godziny przełączenia (sensowne wartości domyślne: 06:00/20:00,
  obie do zmiany). Program sam przełącza się między nimi, bez
  restartu, sprawdzane co 30 sekund.

**Zmiana samego trybu pracy** — wejście w tryb automatyczny, wyjście z
niego, albo dostosowanie już aktywnego harmonogramu dzień/noc —
wymaga poziomu **Inżyniera** i trafia do dziennika audytowego. Tylko
zwykły wybór "jednego motywu przy pozostaniu w trybie stałym"
pozostaje otwarty dla każdego.

## Sterowanie motywem z logiki

Program logiki może też bezpośrednio przełączyć motyw, zapisując tag
`System.Theme` (0 = Industrial … 4 = SimCity 2000; zapis poza
zakresem jest ignorowany, poprzedni motyw pozostaje aktywny). Działa
to zawsze, niezależnie od aktualnego trybu pracy, i nie wymaga
żadnego poziomu dostępu, żeby zadziałać.

**Zapis z logiki zawsze ma pierwszeństwo nad trybem automatycznym.**
W chwili, gdy logika ustawi motyw, automatyczne przełączanie
dzień/noc przestaje działać — aż do kolejnej zmiany trybu pracy tutaj,
w Ustawieniach. Okno pokazuje wtedy odpowiednią informację, żeby było
jasne, czemu tryb automatyczny wygląda na skonfigurowany, ale nie
przełącza. To celowe: docelowo reguły przełączania motywu (czujnik
światła, aktywny alarm, stan instalacji) mają należeć do logiki — tryb
automatyczny to rozwiązanie na czas, gdy taka logika jeszcze nie
istnieje, i nigdy nie może z nią rywalizować, gdy już powstanie.

Twój wybór — motyw, tryb pracy i harmonogram dzień/noc — jest
zapamiętywany do następnego uruchomienia programu.
