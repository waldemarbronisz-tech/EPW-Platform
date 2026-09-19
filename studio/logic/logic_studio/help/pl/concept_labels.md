# Etykiety, znaczniki i bity urządzenia

Trzy różne sposoby, żeby wartość policzona w jednym miejscu schematu
trafiła w inne, bez rysowania jednego, długiego przewodu przez cały
schemat. Łatwo je pomylić — poniżej reguła wyboru i to, co je realnie
różni.

| Sposób | Co to jest | Opóźnienie o cykl skanu |
|---|---|---|
| **Bit urządzenia** (DI/DO/AI/AO) | Fizyczny sygnał na konkretnym module ELA/ADA | Nie dotyczy — czytane/pisane bezpośrednio z/do sprzętu |
| **Znacznik** (bit/rejestr wewnętrzny, M./MR./MW.) | Pamięć wewnętrzna projektu, niezwiązana z żadnym fizycznym terminalem | **Tak, może wystąpić** |
| **Etykieta przewodu** | Tekstowa nazwa nadana przewodowi; przewody o tej samej etykiecie są jednym węzłem | Nie — to zwykłe połączenie |

## Znacznik: dlaczego może dać opóźnienie o cykl

Zapis do znacznika (blok "Wyjście bitowe (wewn.)"/"Wyjście rejestru
(wewn.)") nie trafia do pamięci od razu — silnik buforuje wszystkie
zapisy z danego skanu i zatwierdza je dopiero PO obliczeniu wszystkich
bloków w tym skanie. Jeśli więc blok A zapisuje znacznik, a blok B go w
tym samym skanie odczytuje, blok B zobaczy wartość SPRZED zapisu bloku
A — dopiero w NASTĘPNYM skanie zobaczy nową wartość. To jest właśnie
opóźnienie z⁻¹, opisane osobno w [Cykl skanu i opóźnienie o jeden
cykl](help:concept_scan_cycle). Kolejność bloków na schemacie (czy A
jest "przed", czy "za" B) nie ma tu znaczenia — liczy się wyłącznie to,
że zapis i odczyt są rozdzielone przez granicę skanu.

## Etykieta przewodu: jak działa

Przewody noszące **tę samą etykietę są jednym węzłem sieci**, gdziekolwiek
leżą na schemacie — kompilator łączy je dokładnie tym samym połączeniem
pinów, co przewód narysowany ręcznie, więc od tego miejsca w dół
(kolejność wykonania, symulacja, eksport) sieć etykietowana i narysowana
są nie do odróżnienia. Porównanie etykiet **nie zwraca uwagi na wielkość
liter** ("Blokada ZS" i "blokada zs" to ten sam węzeł).

Reguły, które z tego wynikają:

- w grupie o danej etykiecie musi być **dokładnie jedno źródło** (pin
  wyjściowy); brak źródła albo dwa źródła to błąd kompilacji;
- grupa ze źródłem, ale bez żadnego odbiornika, daje ostrzeżenie
  „sygnał nie jest nigdzie odbierany";
- wolny koniec **bez** etykiety to ostrzeżenie „niedokończony przewód".

Etykieta nie wprowadza opóźnienia o cykl skanu — w przeciwieństwie do
znacznika, jest zwykłym połączeniem, tylko bez rysowania przewodu przez
cały schemat.

## Reguła wyboru

- Sygnał fizyczny (prawdziwy wejście/wyjście na module) → bit
  urządzenia, zawsze.
- Sygnał pomocniczy, potrzebny w kilku miejscach TEGO SAMEGO schematu,
  bez opóźnienia → etykieta przewodu.
- Sygnał pomocniczy, gdzie opóźnienie o jeden cykl jest akceptowalne (a
  zwykle jest — dotyczy to tylko relacji między dwoma konkretnymi
  blokami w tym samym skanie), albo wartość, która ma być nazwana i
  widoczna w rejestrze sygnałów → znacznik.
- Zaślepka na przewodzie, który dopiero zamierzasz podłączyć → wolny
  koniec bez etykiety (patrz [Zaślepka wejścia, wolny koniec przewodu,
  etykieta](help:concept_stubs) — to TRZECIA, osobna rzecz, mimo że
  wygląda podobnie).
