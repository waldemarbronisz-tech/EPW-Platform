# Życie linii i wykrywanie ciszy

To nie jest autotest — program nigdy aktywnie nie odpytuje czujki, bo
wiele z nich tego nie obsługuje. To bierna obserwacja, prowadzona
automatycznie dla każdej linii dozorowej, bez żadnej konfiguracji:

- liczba naruszeń zarejestrowanych od dodania linii
- kiedy było ostatnie naruszenie
- łączny czas spędzony w stanie naruszenia
- kiedy zarejestrowano pierwsze naruszenie

Wykorzystuje ten sam sposób przechowywania danych, którego program już
używa do liczników zużycia mechanicznego urządzeń, zapisywany tak samo
trwale — zamiast budować dla tego drugi, równoległy mechanizm.

**Maksymalny czas bez naruszenia** (poziom Engineer, per linia, okno
Konfiguruj linie) — opcjonalny, 0 = wyłączone. Jeśli linia tak długo nie
zarejestruje ani jednego naruszenia, zostaje oznaczona jako
**Podejrzana**: prawdopodobnie martwa czujka albo urwany kabel, który
akurat spoczywa w pozycji bezpiecznej. To **ostrzeżenie, nie alarm** —
widoczne na stronie Podgląd i zapisywane do dziennika
audytowego, ale nigdy nie wywołuje alarmu ani nie wpływa na uzbrajanie.
Sprawna, spokojna czujka i martwa czujka wyglądają z zewnątrz
identycznie; to tylko sygnalizuje *możliwość* awarii po niezwykle
długiej ciszy, żeby ktoś to sprawdził.
