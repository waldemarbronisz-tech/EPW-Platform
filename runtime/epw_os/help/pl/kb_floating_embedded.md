# Klawiatura pływająca i wbudowana w okno PIN

W programie są dwa OSOBNE rozwiązania klawiatury ekranowej, celowo
zbudowane inaczej.

## Klawiatura pływająca

Osobne, przesuwalne i zmieniające rozmiar okienko, które pojawia się
obok pola tekstowego w zwykłych tabelach (opisy wejść/wyjść cyfrowych,
opisy i notatki punktów analogowych). Sterowana przełącznikiem
[Włączanie](help://kb_enable) w Ustawieniach. Automatycznie dobiera
pełną klawiaturę alfanumeryczną albo wyłącznie numeryczną, zależnie od
typu pola.

## Klawiatura wbudowana w okno PIN

Okna wpisywania PIN-u (logowanie na wyższy poziom, zmiana PIN-u) mają
**wbudowany** klawiszownik numeryczny — nie osobne okienko, tylko część
tego samego okna. Jest widoczny **zawsze**, niezależnie od stanu
przełącznika klawiatury pływającej w Ustawieniach.

## Dlaczego to rozróżnienie istnieje

Osobne, pływające okienko klawiatury nie mogło niezawodnie wpisywać
znaków do pola wewnątrz okna modalnego (takiego jak okno PIN) — modalne
okno w Qt blokuje dostarczanie zdarzeń z innych, osobnych okien.
Zamiast naprawiać tę komunikację między oknami, klawiaturę numeryczną
wbudowano bezpośrednio w samo okno PIN, gdzie ten problem strukturalnie
nie występuje. A ponieważ na urządzeniu bez fizycznej klawiatury
wyłączenie klawiatury pływanej w Ustawieniach nie może odciąć jedynej
drogi wpisania PIN-u (w tym PIN-u potrzebnego, żeby wejść w Ustawienia
i włączyć ją z powrotem) — klawiszownik PIN-u nie zależy od tego
przełącznika w ogóle.

Fizyczna klawiatura, tam gdzie jest podłączona, działa zawsze
równolegle do obu rozwiązań — żadne z nich jej nie zastępuje.
