Trzywejściowa odmiana [NOR](help:block:logic.nor): TRUE tylko wtedy, gdy
**żadne** z trzech wejść nie jest TRUE.

### Przykład: gotowość „brak przeszkód”

`Drzwi otwarte` NOR `Awaria napędu` NOR `Serwis` → `M.GOTOWY`. Każde
nowe źródło blokady to jedno wejście więcej.

### Przykład 2: zezwolenie na otwarcie bramy

`Pojazd w świetle bramy` NOR `Ruch w strefie` NOR `Blokada serwisowa`
→ zezwolenie na zamknięcie automatyczne. Wystarczy jeden z warunków,
by zezwolenie zniknęło — dokładnie to, czego oczekuje się od blokady.
