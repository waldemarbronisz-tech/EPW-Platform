# Linie dozorowe

Jedna linia = jedna czujka (albo pętla czujek) na jednym punkcie
wejściowym. Tabela pokazuje id, nazwę, strefę, typ i skrót konfiguracji;
reszta jest w oknie **Konfiguruj…** — czternaście pól to nie jest wiersz
tabeli.

Bez [strefy](help://zones) nie da się dodać linii.

## Typy linii

| Typ | Kiedy alarmuje |
|---|---|
| **Natychmiastowa** | w chwili naruszenia, ale tylko przy UZBROJONEJ strefie |
| **Zwłoczna** | naruszenie przy uzbrojonej strefie uruchamia odliczanie wejścia; alarm dopiero, gdy nikt nie rozbroi |
| **Całodobowa** | natychmiast, **niezależnie od stanu strefy** — sabotaż, chroniona szafka |
| **Dozorowa** | **nigdy** nie alarmuje przy naruszeniu; sygnalizuje je logice (np. sterowanie oświetleniem). *Awaria* tej linii alarmuje jak w każdym innym typie |
| **Napadowa** | jak całodobowa — każdy stan strefy, także dozór nocny — ale **domyślnie cicha**: sens przycisku napadowego polega na tym, że stojący nad tobą człowiek się nie dowiaduje |

## Wejście

**Tryb stykowy** — zwykły styk: punkt plus stan normalny **NC**
(normalnie zwarty) albo **NO** (normalnie rozwarty). Linia czyta się
tylko jako spoczynek albo naruszenie.

**Tryb parametryzowany (EOL/2EOL)** — rezystor na końcu linii,
pojedynczy (EOL) albo podwójny (2EOL). Wtedy z jednej wartości
analogowej wychodzi pięć stanów, a nie dwa: **Spoczynek**, **Naruszenie**,
**Przerwa**, **Zwarcie**, **Sabotaż**. Okna wartości (min/max
w jednostkach inżynierskich) ustawiasz w tabeli poniżej — po jednym
wierszu na stan.

Właśnie dlatego 2EOL wykrywa przecięcie i zmostkowanie przewodu, czego
zwykły styk nie potrafi.

## Filtrowanie fałszywych alarmów

| Nastawa | Do czego |
|---|---|
| **Czas potwierdzenia (czułość)** | naruszenie krótsze niż to jest ignorowane |
| **Krotność naruszeń** | alarm dopiero po N naruszeniach |
| **Okno krotności** | w jakim czasie mają się zmieścić |
| **Blokada po liczbie alarmów** | linia „szalejąca" przestaje alarmować do rozbrojenia |
| **Czas podtrzymania alarmu** | jak długo strefa zostaje w ALARM po ustaniu przyczyny |

## Nadzór linii

**Czas ciszy przed podejrzeniem** — jeśli linia nie zgłosiła naruszenia
przez tak długo, dostaje status „podejrzana". To **ostrzeżenie, nie
alarm**: czujka, która nigdy nic nie widzi, bywa czujką martwą.

## Dozór nocny

**Czuwa nocą** — odznaczone znaczy, że ta linia przestaje dozorować, gdy
strefa jest uzbrojona w trybie nocnym. Zwykły wybór dla czujek ruchu
wewnątrz: ludzie chodzą po domu, a perymetr dalej czuwa. Linia
całodobowa i napadowa alarmują niezależnie od tego.
