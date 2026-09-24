Czterowejściowa odmiana [NOR](help:block:logic.nor): TRUE tylko wtedy, gdy
**żadne** z czterech wejść nie jest TRUE.

### Przykład: cisza w rozdzielni

Cztery bity alarmowe pól → jedna lampka „BRAK ALARMÓW”. Odwrotność
przykładu z [OR-4](help:block:logic.or4).

### Przykład 2: warunek „nic nie pracuje” przed serwisem

`Pompa 1 pracuje` NOR `Pompa 2 pracuje` NOR `Mieszadło pracuje` NOR
`Grzałka pracuje` → zezwolenie na otwarcie włazu serwisowego. Dopóki
cokolwiek pracuje, zezwolenia nie ma.
