Czterowejściowa odmiana bramki [AND](help:block:logic.and): TRUE tylko
wtedy, gdy **wszystkie cztery** wejścia są TRUE.

### Przykład: gotowość sekcji rozdzielni

`Q1 zamknięty` AND `Napięcie na szynie` AND `Brak zadziałania
zabezpieczeń` AND `Tryb AUTO` → `M.SEKCJA_GOTOWA`. Wejście, którego w
danym obiekcie nie ma (np. brak sygnału trybu), **zaślep** zamiast
zostawiać niepodłączone — niepodłączone wejście to FALSE, a więc
gotowości nie będzie nigdy.
