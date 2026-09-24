# Bity wewnętrzne logiki

Strona **Bity wewnętrzne** pokazuje na żywo bity z rejestru programu
logiki (`M.<nazwa>`, `MR.` retentive, `MW.`/`MWR.` rejestry liczbowe),
tak jak je zadeklarowano w Studiu, w dziale Sygnały.

**Kierunek** liczy się z punktu widzenia logiki:

- **WE (wejściowy)** — ustawia ktoś spoza logiki, logika tylko czyta.
  Kto ma prawo pisać, mówi wpis bitu w projekcie: panel od podanego
  poziomu dostępu (kolumna *Kto pisze*), wymuszenie ze Studia zawsze,
  REST/MQTT/Home Assistant tylko gdy projektant to włączył.
- **WY (wyjściowy)** — pisze wyłącznie logika; panel tylko go pokazuje.

Przyciski **USTAW / KASUJ** (albo *Wartość…* dla rejestru) są aktywne
tylko przy bicie WE i tylko na poziomie dostępu, którego wymaga wpis.
Każdy zapis z panelu trafia do dziennika audytowego ze starą i nową
wartością; odmowa też, z powodem.

**Zezwolenie aparatu.** W rejestrze aparatów Studia można wskazać bit WY
jako zezwolenie na załączenie. Gdy nie jest on TRUE, polecenie ZAMKNIJ
jest odrzucane z powodem nazywającym bit, np. *ZAMKNIJ KOT_KMG1
odrzucone: brak zezwolenia M.KMG1_ZEZW (Blokada od Q1 otwartego)*.
OTWÓRZ nigdy nie jest blokowane. Zatrzymana logika, bit nieznany albo
sterownik przed pierwszym skanem oznaczają brak zezwolenia. Tor
zabezpieczeniowy ADA01 nie zależy od żadnego bitu logiki.
