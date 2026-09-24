# Przerzutniki i detekcja zboczy

Bramki liczą stan „teraz”. Gdy logika ma **pamiętać** (napęd pracuje po
puszczeniu przycisku, alarm trwa do skasowania) albo reagować na
**moment** zmiany, a nie na stan (jedno naciśnięcie = jedno zliczenie),
potrzebne są bloki stanowe z tej strony.

## Przerzutniki SR i RS

| | S i R naraz | Kiedy wybrać |
|---|---|---|
| [SR](help:block:memory.sr) | wygrywa **S1** (Set) | pamięć alarmu: kasowanie nie działa, dopóki przyczyna trwa |
| [RS](help:block:memory.rs) | wygrywa **R1** (Reset) | napędy: STOP/awaria/blokada zawsze wygrywa ze START |

Oba pamiętają Q między skanami; przy starcie logiki Q = FALSE. Ustawienie
i kasowanie może przyjść z różnych źródeł (przycisk fizyczny, bit WE z
panelu albo z przycisku na synoptyce, wynik innej logiki) — zbierz je
bramką [OR](help:block:logic.or) przed wejściem.

Reguła bezpieczeństwa: jeśli którekolwiek z wejść R to STOP, wyłącznik
bezpieczeństwa albo blokada, użyj **RS**. Set-dominant SR jest właściwy
tam, gdzie ważniejsze jest **nie zgubić** zdarzenia (pamięć alarmu).

## Detekcja zboczy

| Blok | Impuls (jeden skan), gdy… |
|---|---|
| [R_TRIG](help:block:edge.rtrig) | wejście zmieniło się 0→1 |
| [F_TRIG](help:block:edge.ftrig) | wejście zmieniło się 1→0 |
| [CHANGE](help:block:edge.change) | wejście zmieniło się w którąkolwiek stronę |

Wyjście trwa **dokładnie jeden skan**. Dla oka (lampka) i dla wolnych
odbiorników to za krótko — wydłuż je timerem [TOF](help:block:timer.tof)
albo [TP](help:block:timer.tp). Dla liczników i przerzutników jeden skan
wystarcza.

Przy pierwszym skanie po starcie logiki „poprzedni stan” jest FALSE:
wejście, które od razu jest TRUE, da jeden impuls R_TRIG/CHANGE. Jeżeli
to niepożądane (np. zliczanie), zablokuj je na czas rozruchu warunkiem z
[TON](help:block:timer.ton).

## Trzy klasyczne połączenia

1. **Przełącz przyciskiem** (toggle): `Przycisk` → R_TRIG → CU licznika
   [CTUD](help:block:counter.ctud); stan = CV nieparzyste. Albo prościej:
   przycisk na synoptyce w trybie „przełączanie” pisze bit WE sam.
2. **Zdarzenie „skończył się cykl”**: F_TRIG(`Cykl trwa`) → S przerzutnika
   następnego kroku sekwencji.
3. **Alarm z pamięcią**: `Przyczyna` → S1 SR, `Kasuj` → R, Q → lampa.
   Kasowanie działa dopiero, gdy przyczyna zniknie.

Szczegóły i więcej przykładów: [Typowe układy
sterowania](help:guide_typical_circuits).
