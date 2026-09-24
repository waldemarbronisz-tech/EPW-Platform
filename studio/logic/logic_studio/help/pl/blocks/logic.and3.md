Trzywejściowa odmiana bramki [AND](help:block:logic.and): wyjście jest
TRUE tylko wtedy, gdy **wszystkie trzy** wejścia są TRUE. Tabela prawdy i
zasady — jak dla AND dwuwejściowej.

### Przykład: zezwolenie ruchu napędu

`Zasilanie OK` AND `Brak awarii` AND `Osłona zamknięta` → `M.NAPED_ZEZW`.
Jeśli kiedyś dojdzie czwarty warunek, wymień blok na
[AND-4](help:block:logic.and4) — przewody zostają, dochodzi jedno wejście.
Gdy warunków jest więcej niż cztery, złóż dwie bramki kaskadowo
(wyjście pierwszej na wejście drugiej) albo zamknij warunki w
[makro](help:concept_macros).
