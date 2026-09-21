# 3.3 Adresacja kanalow

Format adresu kanalu to `KARTA.RODZAJ.KANAL`, na przyklad `ELA1.DI.12` albo `ADA1.DO.4`. Rodzaj to jeden z DI (wejscie cyfrowe), DO (wyjscie cyfrowe), AI (wejscie analogowe), AO (wyjscie analogowe). Numeracja kanalow zaczyna sie od 1, nie od 0.

Biale znaki wokol calego adresu lub wokol kazdej z trzech czesci sa ignorowane przy porownywaniu - `ELA1.DI.12` i ` ELA1 . DI . 12 ` to ten sam adres dla wykrywania kolizji. Wiodace zera tez nie maja znaczenia: `ELA1.DI.12` i `ELA1.DI.012` rowniez licza sie jako ten sam, jeden fizyczny kanal.

W samym formularzu aparatu adres nigdy nie jest wpisywany recznie jako tekst - picker kanalu ([4.8](help://synoptic/dev-form-validation)) to trzy powiazane pola (karta, wtedy dostepny rodzaj wynika z karty, wtedy numer kanalu z listy 1..liczba_kanalow tej karty), wiec zly format jest praktycznie niemozliwy do wprowadzenia przez interfejs. Sam tekstowy format ma znaczenie przy odczytywaniu pliku projektu recznie albo z zewnetrznego zrodla.
