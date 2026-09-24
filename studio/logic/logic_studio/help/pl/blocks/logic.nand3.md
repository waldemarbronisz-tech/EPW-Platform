Trzywejściowa odmiana [NAND](help:block:logic.nand): FALSE tylko wtedy,
gdy **wszystkie trzy** wejścia są TRUE, inaczej TRUE.

### Przykład: ograniczenie liczby pracujących odbiorów

Trzy grzałki na jednym obwodzie — trzecia nie może się załączyć, gdy dwie
już grzeją: `Grzałka 1` NAND `Grzałka 2` NAND `Grzałka 3` daje FALSE
dopiero przy trzech naraz; użyj tego jako blokady na wejściu AND
zezwolenia trzeciej.
