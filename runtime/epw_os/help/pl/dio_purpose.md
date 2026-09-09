# Do czego służą te strony

**Digital Inputs** pokazuje stan 64 wejść cyfrowych (DI1–DI64) — sygnały
odbierane z instalacji (np. stan krańcówki, sygnalizacja zewnętrzna).

**Control Outputs** pokazuje 64 wyjścia cyfrowe (DO01–DO64) — sygnały
wysyłane do instalacji (np. sterowanie stycznikiem). Pierwsze cztery
wyjścia (DO01–DO04) mają rzeczywiste sprzężenie zwrotne z wejść
DI1–DI4 — ich stan na ekranie pochodzi z powrotnego sygnału, a nie z
samej komendy. Pozostałe wyjścia (DO05–DO64) są samodzielne — ich
własny tag jest jednocześnie komendą i sprzężeniem zwrotnym.

Obie strony mają ten sam układ: adres (etykieta w stylu sterownika
PLC — wyłącznie informacyjna, %IX0.N / %QX0.N), tag, opis, stan,
kontrolka LED i znacznik czasu ostatniej zmiany.
