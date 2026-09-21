# 4.6 MEASURED - pomiarowe

MEASURED to wejscie pomiarowe analogowe: temperatura, cisnienie, przeplyw. Pola: input (adres kanalu AI), unit (jednostka, np. "°C"), rangeMin/rangeMax (zakres, rangeMin musi byc mniejszy niz rangeMax), format (np. "0.0" - liczba cyfr po kropce odpowiada liczbie zer w tym tekscie) i deadband (strefa martwa wokol wartosci, >= 0).

Edytor nie ma zywych danych, wiec podglad w formularzu pokazuje SRODEK skonfigurowanego zakresu (np. 0..400 daje podglad 200), sformatowany zgodnie z polem format - nigdy zmyslonej liczby.

Kreator miernika ([7.1](help://synoptic/elem-meter)) pokazuje wylacznie aparaty MEASURED, pogrupowane po jednostce - dlatego aparat musi istniec i miec zachowanie MEASURED, zanim pojawi sie na liscie do wyboru w kreatorze.
