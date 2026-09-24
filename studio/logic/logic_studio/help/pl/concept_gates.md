# Bramki logiczne: jak je czytać i do czego służą

Bramka logiczna liczy jedną wartość TRUE/FALSE z jednej, dwóch, trzech
albo czterech wartości wejściowych. Wynik jest gotowy w tym samym skanie
(bez opóźnienia — patrz [Cykl skanu](help:concept_scan_cycle)); bramka
nie ma pamięci, jej wyjście zależy wyłącznie od tego, co jest na
wejściach **teraz**. Pamięć dają [przerzutniki](help:concept_memory_edges),
czas — [timery](help:concept_timers).

Na każdej stronie bramki w Katalogu bloków jest **tabela prawdy**,
**animacja** ze schematu w symulacji (zielone przewody i porty = TRUE,
czarne = FALSE) i **przykłady zastosowania** z praktyki obiektowej.

## Rodzina

| Bramka | Wyjście TRUE, gdy… | Typowe użycie |
|---|---|---|
| [AND](help:block:logic.and) ([AND-3](help:block:logic.and3), [AND-4](help:block:logic.and4)) | **wszystkie** wejścia TRUE | zezwolenie: wszystkie warunki naraz |
| [OR](help:block:logic.or) ([OR-3](help:block:logic.or3), [OR-4](help:block:logic.or4)) | **którekolwiek** wejście TRUE | alarm zbiorczy, stop z kilku miejsc |
| [NOT](help:block:logic.not) | wejście FALSE | styk rozwierny, negacja warunku |
| [NAND](help:block:logic.nand) (-3, -4) | **nie wszystkie** wejścia TRUE | blokada „nie oba naraz” |
| [NOR](help:block:logic.nor) (-3, -4) | **żadne** wejście nie jest TRUE | lampka „wszystko w porządku” |
| [XOR](help:block:logic.xor) | wejścia **różne** | niezgodność potwierdzeń, schodowy |
| [XNOR](help:block:logic.xnor) | wejścia **jednakowe** | zgodność polecenia z potwierdzeniem |
| [BUFOR](help:block:logic.buffer) | wejście TRUE (przepisanie) | punkt rozgałęzienia, miejsce na późniejszą logikę |

## Zasady wspólne dla wszystkich bramek

1. **Wejście niepodłączone to FALSE.** AND z jednym pustym wejściem nigdy
   nie da TRUE; OR z pustym wejściem po prostu go nie widzi. Kompilator
   ostrzega o niepodłączonych wejściach — nie ignoruj tego.
2. **Zaślepka** (tylko bramki 2+ wejściowe) wyłącza wejście z liczenia:
   AND-4 z jednym zaślepionym wejściem liczy jak AND-3. Używaj jej
   świadomie, gdy warunku w danym obiekcie nie ma — patrz [Zaślepka
   wejścia, wolny koniec przewodu, etykieta](help:concept_stubs).
3. **Więcej niż cztery wejścia**: kaskada (wyjście jednej bramki na
   wejście drugiej — AND(AND(a,b,c,d), AND(e,f)) to AND sześciu) albo
   [makro](help:concept_macros) z czytelną nazwą.
4. **Negacja na wejściu**: nie ma osobnego „kółka negacji” na pinie —
   wstaw [NOT](help:block:logic.not) przed wejściem. Przy kilku negacjach
   rozważ NOR/NAND, które często zastępują NOT + OR/AND jednym blokiem.
5. **Sygnał z panelu i z logiki**: bit WE (pisany przez panel, przycisk
   na synoptyce, REST) czytasz blokiem „Wejście bitowe (wewn.)” i
   podajesz na bramkę jak każdy inny sygnał; wynik bramki piszesz blokiem
   „Wyjście bitowe (wewn.)” do bitu WY — to ten bit jest np.
   zezwoleniem aparatu na sterowniku. Patrz [Etykiety, znaczniki i bity
   urządzenia](help:concept_labels).

## Jak dobrać bramkę — trzy pytania

- Czy wynik ma być TRUE, gdy **wszystkie** warunki są spełnione (AND), czy
  gdy **którykolwiek** (OR)?
- Czy interesuje mnie stan **spełniony**, czy **niespełniony**? Jeśli
  niespełniony — NAND/NOR/NOT zamiast dodatkowego bloku negacji.
- Czy porównuję dwa sygnały ze sobą (XOR: różne, XNOR: jednakowe)?

Gdy do warunków dochodzi **czas** („przez 2 s”, „po 5 s”, „na 200 ms”)
albo **pamięć** („aż do skasowania”), bramka nie wystarczy — sięgnij po
[timery](help:concept_timers) i [przerzutniki](help:concept_memory_edges).
Gotowe, sprawdzone połączenia tych bloków są w [Typowych układach
sterowania](help:guide_typical_circuits).
