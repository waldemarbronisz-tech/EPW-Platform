# Nadzór zasilania

Pojedyncze, ogólne ustawienie strony (nie per strefa, nie per linia)
pilnujące, czy zasilanie sieciowe i akumulator zapasowy faktycznie są
sprawne — **Nadzór zasilania...** na stronie Konfiguracja (poziom
Engineer).

Skonfiguruj do dwóch, w pełni niezależnych i opcjonalnych wejść:
- wejście **obecności zasilania sieciowego** i który z jego dwóch
  stanów oznacza "zasilanie sprawne"
- wejście **stanu akumulatora** i który z jego dwóch stanów oznacza
  "akumulator sprawny"

Pozostawienie któregoś pustym oznacza po prostu brak nadzoru nad nim —
bez błędu, bez niczego widocznego, dokładnie tak, jakby ta funkcja nie
istniała. Skonfiguruj tylko to, co masz, albo żadne z nich.

Niesprawne zasilanie sieciowe albo akumulator podnoszą **alarm
techniczny** — osobną kategorię od alarmu włamaniowego, bo problem z
zasilaniem to nie włamanie. Zapisywany jest do dziennika audytowego i
wystawiany jako tagi (patrz [Sygnały dla logiki](help://intr_tags)) —
`Security.System.TechnicalAlarm` oraz per-wejściowe `Security.Power.
MainsOk`/`BatteryOk` — żeby logika mogła zareagować (np. sterując
wskaźnikiem albo powiadomieniem). Żadna strona w tym programie nie
pokazuje go dziś sama z siebie na ekranie — zobaczenie go dziś oznacza
sprawdzenie Dziennika audytowego, obejrzenie samego tagu (np. z
Trendów albo przez REST API), albo zareagowanie na niego z poziomu
logiki.

**Zanik zasilania sieciowego nigdy nie blokuje uzbrajania ani
rozbrajania** — te dwie rzeczy są całkowicie niezależne. Strefa uzbraja
się i rozbraja dokładnie tak samo, niezależnie od bieżącego stanu
zasilania.
