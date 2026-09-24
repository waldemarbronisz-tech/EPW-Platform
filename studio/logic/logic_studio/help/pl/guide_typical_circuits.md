# Typowe układy sterowania — gotowe połączenia bloków

Osiem układów, które wracają w każdym projekcie. Każdy jest opisany
blokami z biblioteki (link prowadzi na stronę bloku z tabelą prawdy,
animacją i przykładami). Nazwy sygnałów są przykładowe — w projekcie
użyj adresów DI/DO z Rejestru punktów i bitów z rejestru bitów.

## 1. Start/stop napędu z podtrzymaniem i priorytetem stopu

```
DI START ─────────────────────┐
                              ├─ S ─┐
DI STOP (NC) ── NOT ──┐       │     │ RS ── Q ── DO STYCZNIK
M.AWARIA ─────────────┼─ OR-3 ┴─ R1 ┘
M.BLOKADA ────────────┘
```

Bloki: [NOT](help:block:logic.not) (styk rozwierny), [OR-3](help:block:logic.or3),
[RS](help:block:memory.rs) (reset dominuje: STOP wygrywa ze START).
Podtrzymanie bierze się z pamięci przerzutnika — krótki impuls START
wystarcza.

## 2. Zezwolenie aparatu (blokada twarda na sterowniku)

```
DI Q1 ZAMKNIĘTY ──┐
M.BRAK_AWARII ────┼─ AND-3 ── Wyjście bitowe (wewn.) M.KMG1_ZEZW
M.TRYB_AUTO ──────┘
```

Wynik trafia do bitu **WY** [AND-3](help:block:logic.and3) → „Wyjście
bitowe (wewn.)”. W Studiu, w Rejestrze aparatów, wskaż `M.KMG1_ZEZW`
jako **Zezwolenie** aparatu KMG1: sterownik odrzuci polecenie ZAŁĄCZ z
powodem „brak zezwolenia M.KMG1_ZEZW (opis bitu)”, a WYŁĄCZ przepuści
zawsze. Punkt DO bez aparatu ma własne pole Zezwolenie w Rejestrze
punktów.

## 3. Nadzór wykonania polecenia

```
M.POLECENIE_ZAL ─────────┐
                         ├─ AND ── TON 2000 ms ── Q ── SR S1 ── Q ── M.ALARM_BRAK_POTW
DI POTW_ZAL ──── NOT ────┘                              ▲
M.KASUJ (bit WE z panelu) ──────────────────────────── R
```

[TON](help:block:timer.ton) daje aparatowi czas na przełączenie; gdy
potwierdzenie nie przyjdzie, [SR](help:block:memory.sr) pamięta alarm do
skasowania z panelu (bit WE, zapis audytowany).

## 4. Niezgodność dwóch styków pomocniczych

```
DI STYK_ZAMKNIĘTY ──┐
                    ├─ XOR ── NOT ── TON 1000 ms ── M.NIEZGODNOSC
DI STYK_OTWARTY ────┘
```

[XOR](help:block:logic.xor) = FALSE, gdy oba styki mówią to samo (oba
aktywne albo żaden); [NOT](help:block:logic.not) zamienia to na TRUE, a
[TON](help:block:timer.ton) pomija czas ruchu styków.

## 5. Wybieg wentylatora

```
DO GRZAŁKA (stan) ── TOF 60000 ms ── DO WENTYLATOR
```

[TOF](help:block:timer.tof): wentylator pracuje z grzałką i jeszcze
minutę po niej.

## 6. Impuls na cewkę i ochrona przed powtórnym startem

```
DI PRZYCISK ── R_TRIG ── TP 200 ms ── DO CEWKA_ZAL
                          └─ Q ── NOT ── (warunek zezwolenia na kolejny impuls)
```

[R_TRIG](help:block:edge.rtrig) zamienia trzymany przycisk w jedno
zdarzenie, [TP](help:block:timer.tp) daje cewce dokładnie 200 ms.

## 7. Sygnalizacja migająca

```
GENERATOR 1 Hz ──┐
                 ├─ AND ── DO LAMPA
M.ALARM ─────────┘
```

Blok generatora systemowego daje falę prostokątną; [AND](help:block:logic.and)
z bitem alarmu daje miganie tylko w alarmie. Lampa ciągła = bit alarmu
bezpośrednio.

## 8. Zliczanie łączeń do przeglądu

```
DI POTW_ZAMKNIĘTY ── R_TRIG ── CU ┐
                                  ├─ CTU (PV=10000) ── Q ── M.PRZEGLAD
M.KASUJ_LICZNIK (bit WE) ───── R ┘
```

[CTU](help:block:counter.ctu) liczy zamknięcia, Q zgłasza przegląd,
kasowanie z panelu po przeglądzie. O trwałości CV po restarcie — patrz
[Liczniki](help:concept_counters).

## Jak sprawdzić układ przed wysłaniem na obiekt

1. [Skompiluj](help:guide_compile_export) — zero błędów, przejrzyj
   ostrzeżenia o niepodłączonych wejściach.
2. [Uruchom symulację](help:guide_simulation) i przełączaj wejścia w
   panelu symulacji — przewody i porty pokazują stan na żywo, dokładnie
   tak jak na animacjach w Katalogu bloków.
3. Sprawdź przypadki brzegowe: oba przyciski naraz, zanik warunku w
   trakcie odliczania timera, restart (stan początkowy przerzutników i
   liczników to FALSE/0).
