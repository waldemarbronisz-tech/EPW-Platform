# Plik projektu nie chce sie otworzyc

OBJAW: File > Open... na wybranym pliku konczy sie komunikatem bledu zamiast otworzyc projekt.

PRZYCZYNA: jedna z trzech mozliwosci - plik nie jest poprawnym JSON-em (blad parsowania), pole `format` nie jest rowne `"EPW_SYNOPTIC"` (to plik innego programu albo innego formatu, np. wspomniany w [10.1](help://synoptic/file-contents) EPW_PROJECT), albo `schema_version` jest wyzszy niz obslugiwany przez ta wersje edytora ([10.2](help://synoptic/file-versioning)).

CO ZROBIC: przeczytaj dokladna tresc bledu w panelu Messages - kazdy z trzech przypadkow ma osobny, konkretny komunikat. Plik z za nowa wersja wymaga nowszej wersji edytora; zly format nie jest plikiem tego programu.
