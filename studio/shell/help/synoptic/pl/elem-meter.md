# 7.1 Miernik

UWAGA: sa DWA rozne "mierniki" w tym edytorze. Statyczny symbol SCADA "Meter (SCADA)" z biblioteki to zwykla grafika bez wierszy i bez wlasnego stanu - jak kazdy inny symbol. Ten rozdzial opisuje DRUGI, dynamiczny element Miernik (przycisk w toolbarze), zbudowany z wierszy.

Miernik ma dowolna liczbe wierszy; kazdy wiersz albo wskazuje na aparat MEASURED (jednostka, format i wartosc podgladu - srodek zakresu - pochodza ZAWSZE z aparatu, nigdy nie sa kopiowane na wiersz), albo jest wierszem recznym z wlasna wartoscia i jednostka wpisana wprost. Wysokosc miernika jest ZAWSZE wyliczana z liczby wierszy, obecnosci tytulu i rozmiaru czcionki - nie ma pola wysokosci do recznego ustawienia.

Kreator wyboru pomiarow (przycisk Kreator...) pokazuje WYLACZNIE aparaty o zachowaniu MEASURED, pogrupowane po jednostce - jesli lista jest pusta, w projekcie nie ma jeszcze zadnego aparatu MEASURED (patrz [4.6](help://synoptic/dev-measured) i [rozdzial 11](help://synoptic/ts-meter-wizard-empty)).

Wiersz wskazujacy na aparat, ktory nie istnieje albo nie ma zachowania MEASURED, jest oznaczany kolorem MISSING zamiast rzucac wyjatek.
