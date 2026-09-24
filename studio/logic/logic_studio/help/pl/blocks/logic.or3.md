Trzywejściowa odmiana bramki [OR](help:block:logic.or): TRUE, gdy
**którekolwiek** z trzech wejść jest TRUE.

### Przykład: stop z trzech źródeł

`STOP panel` OR `STOP zdalny` OR `Wyłącznik krańcowy` → wejście R
przerzutnika trzymającego pracę napędu. Uwaga: przycisk STOP bywa stykiem
rozwiernym (NC) — wtedy do bramki podaj jego negację ([NOT](help:block:logic.not)),
żeby OR liczył „naciśnięty”, a nie „zwolniony”.
