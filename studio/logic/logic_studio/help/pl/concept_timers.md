# Timery TON, TOF, TP

Trzy timery odpowiadają na trzy pytania o czas: **po jakim czasie**
załączyć (TON), **jak długo jeszcze** trzymać po wyłączeniu (TOF) i
**na ile** załączyć niezależnie od wejścia (TP). Wszystkie mają te same
piny: IN (start/warunek), PT (czas w ms — pin ma pierwszeństwo przed
właściwością „Preset (ms)”), Q (wyjście) i ET (czas, który upłynął,
w ms, nigdy więcej niż PT).

Czas liczy zegar silnika: w symulacji zegar symulacyjny (deterministyczny,
krok = okres skanu), na sterowniku zegar monotoniczny. Rozdzielczość to
jeden skan — timer 300 ms przy skanie 100 ms zadziała po 3 skanach.

## TON — opóźnienie załączenia ([strona bloku](help:block:timer.ton))

```
IN  ‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾___________
Q   ___________|‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾___________
    |<-- PT -->|
```

Q = TRUE, gdy IN trwa nieprzerwanie PT. Spadek IN zeruje Q i czas
natychmiast. Typowe: filtr drgań styku, nadzór „czy potwierdzenie
przyszło na czas”, sekwencja rozruchu, opóźniony alarm.

## TOF — opóźnienie wyłączenia ([strona bloku](help:block:timer.tof))

```
IN  ______|‾‾‾‾‾‾‾‾‾‾‾‾|______________________________
Q   ______|‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾|__________________
                       |<-- PT --->|
```

Q = TRUE od razu z IN i jeszcze PT po jego spadku. Powrót IN w czasie
odliczania przedłuża Q (odliczanie zaczyna się od nowa przy kolejnym
spadku). Typowe: wybieg wentylatora, światło z czujnika ruchu,
wydłużenie krótkiego impulsu.

## TP — impuls ([strona bloku](help:block:timer.tp))

```
IN  ____|‾‾|______|‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾|______
Q   ____|‾‾‾‾‾‾‾|_|‾‾‾‾‾‾‾|_______________
        |<-PT->|  |<-PT->|
```

Zbocze narastające IN daje impuls Q o długości dokładnie PT, obojętnie
jak długo trwa IN. W czasie impulsu nowe zbocza są ignorowane. Typowe:
impuls na cewkę, sygnał dźwiękowy, blokada zbyt częstych startów.

## Trzy pułapki

1. **PT z pinu kontra właściwość.** Gdy pin PT jest podłączony, wartość
   właściwości „Preset (ms)” nie jest używana — nawet jeśli na kanwie
   widać „T=…[s]”. Podłączony PT bez wartości (None) oznacza właściwość.
2. **Timer w pętli sprzężenia zwrotnego** (np. Q timera przez bramkę na
   jego własne IN) oddaje wartość z poprzedniego skanu — patrz [Cykl skanu
   i opóźnienie o jeden cykl](help:concept_scan_cycle).
3. **Stop i restart symulacji** zerują stan timera (start liczony od
   nowa); **Pauza** go zachowuje.

Rozrysowane układy z timerami: [Typowe układy
sterowania](help:guide_typical_circuits).
