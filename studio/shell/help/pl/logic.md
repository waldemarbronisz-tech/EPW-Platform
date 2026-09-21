# Logika

Pełny opis edytora logiki — pojęcia (etykiety, znaczniki, cykl skanu),
poradniki, katalog każdego bloku i skróty — jest w tej samej pomocy,
w dziale [Logika — edytor logiki](help://logic/welcome); F1 na
zaznaczonym bloku otwiera jego stronę z katalogu.

Edytor logiki sterowania (Logic Studio) jako dział Studia — biblioteka
bloków, symulacja, kompilacja i eksport do sterownika, te same narzędzia
co w samodzielnym Logic Studio, w jednej skórze z resztą działów.

## Na czym się programuje

Na **adresach z tego projektu**: `ELA1.DI.1`, `ADA1.DO.3`, punkty
analogowe z ich zakresem inżynierskim i jednostką. Karty i punkty są
mostkowane do edytora automatycznie — nie przepisujesz ich drugi raz.

Poza nimi masz:

- **bity wewnętrzne** (`M.`) i **bity retencyjne** (`MR.` / `MWR.`),
  które przeżywają restart sterownika;
- **sygnały systemowe `SYS.*`** — stan sterownika, poziom dostępu,
  komunikacja, generatory impulsów i migania;
- **sygnały alarmówki `SSWIN.*`** — uzbrojenie, alarm, pamięć alarmu,
  sabotaż, gotowość, a także sygnalizator i komendy.

## Sygnalizator: to Ty go podpinasz

Sterownik **nie steruje żadną syreną**. Wystawia stan — `SSWIN.SIREN_ACTIVE`
(ma dźwięczeć), `SIREN_TIME_LEFT`, `STROBE_ACTIVE` (lampa), `PANIC` —
a to, na którym wyjściu wisi syrena i przez jakie blokady, jest linią
schematu, którą rysujesz tutaj. Nastawy (jak długo wolno dźwięczeć, czy
linia napadowa ma być cicha) są w [Strefach](help://zones).

Tak samo `SSWIN.CMD_SILENCE` — wyciszenie samego dźwięku, bez ruszania
alarmu.

## Kompilacja i eksport

Logika jedzie na sterownik **skompilowana, w pliku projektu**. Zapis
projektu bierze aktualny wynik kompilacji; jeśli schemat się nie
kompiluje, Studio mówi to wprost i **zostawia poprzednią skompilowaną
wersję** — sterownik nigdy nie dostaje półproduktu.

Po wysłaniu możesz sprawdzić, czy skan naprawdę chodzi: [Połączenie ze
sterownikiem](help://controller) pokazuje liczbę bloków, czas cyklu,
liczbę skanów i ile wyjść prowadzi logika.

## Własna pomoc edytora

Logic Studio ma **własny, pełny dział pomocy**: pojęcia (etykiety kontra
znaczniki, opóźnienie o jeden skan, jakość sygnału analogowego, makra),
przewodniki krok po kroku i **katalog bloków** generowany z żywej
biblioteki — każdy blok z pinami, właściwościami i wartościami
domyślnymi. Otwórz go z poziomu edytora; **F1 na zaznaczonym bloku**
wchodzi od razu w jego opis.
