# Test zabezpieczeń

Wewnętrzny Omicron: sterownik sam wymusza stan, mierzy czas reakcji
i zostawia raport. Bez walizki pomiarowej i bez rozbierania instalacji.

Wymaga tokenu Engineer; każdy test trafia do dziennika, a raporty
zostają **na sterowniku**.

## Co da się przetestować

**Zabezpieczenie procesowe** — punkt analogowy jest wymuszany ponad
próg, czas zadziałania mierzony względem skonfigurowanej zwłoki, potem
wartość wraca w zakres i mierzony jest czas skasowania.

**Aparat** — komenda idzie **tą samą drogą co z panelu**: blokady
logiki, safety kernel, tryb szkoleniowy i wymuszenia działają bez zmian.
Mierzony jest czas sprzężenia zwrotnego, potem stan jest przywracany.

Lista **Co można przetestować** pokazuje rodzaj, id, nazwę, nastawy
i stan: `gotowe`, `wyłączone`, `zadziałane — najpierw skasuj`.

## Czego ten test nie obejmuje

**Ścieżki zabezpieczeń elektrycznych (ADA01).** Funkcje ANSI wykonuje
karta, a nie program sterownika — tego nie da się sprawdzić wymuszeniem
tagu.

## Raporty

Tabela: start, rodzaj, obiekt, wynik, nastawy, **zmierzone**, powód.
Dwuklik otwiera kroki pojedynczego testu — co po kolei zrobił i co
zmierzył.

**Zapisz raporty jako CSV** eksportuje je do pliku, do dokumentacji
odbiorowej.

Starszy EPW-OS bez tej funkcji jest rozpoznawany i mówi to wprost.
