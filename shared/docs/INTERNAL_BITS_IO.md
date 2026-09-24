# Bity wewnętrzne WE/WY — kierunek, pisarze, zezwolenie aparatu

Decyzje właściciela z 2026-09-22. Kod: rejestr i pola
`shared/logic/internal_bits.py`; tagi w sterowniku
`runtime/epw_os/core/logic_runtime.py` (`TagIOProvider`); jedyne drzwi
dla zapisu spoza logiki `runtime/epw_os/core/internal_bit_gate.py`;
bramka zezwolenia `runtime/epw_os/core/command_manager.py`
(`_permission_refusal`); strona panelu
`runtime/epw_os/gui/pages/page_internal_bits.py`; Studio: dział Sygnały
(kolumny Kierunek / Panel / Zdalnie), Rejestr aparatów (kolumna
Zezwolenie), Rejestr punktów (bity z wartością na żywo), „Sprawdź
projekt” (punkt 10).

## Kierunek — z punktu widzenia logiki

| kierunek | kto pisze | kto czyta |
|---|---|---|
| **WE (IN)** | ktoś spoza logiki: panel, wymuszenie ze Studia, REST/MQTT (gdy pozwolono) | logika |
| **WY (OUT)** | wyłącznie logika (skan) | reszta systemu: ekran, zezwolenie aparatu, MQTT |

Bit pisany i czytany tylko przez logikę („drut” między arkuszami) to WY,
którego nikt z zewnątrz nie czyta. Wpis bez pola `direction` (projekt
sprzed tej zmiany) jest WY. Blok „Wyjście bitowe” na bicie WE to błąd
kompilacji.

Na sterowniku każdy bit rejestru jest **tagiem** o nazwie `M.<nazwa>`
(`MR.` retentive, `MW.`/`MWR.` rejestr REAL). Bit WY: pamięć skanu,
kopiowana na tag po każdym skanie; zapis na tag WY „za plecami” logiki
znika w następnym skanie. Bit WE: **jest** tagiem — skan czyta to, co
ostatnio ustawił panel, wymuszenie albo dopuszczony pisarz zdalny.

## Pisarze bitu WE — deklarowani per bit

| pisarz | pole wpisu | domyślnie | zasada |
|---|---|---|---|
| panel/ekran | `panel_level` (`User`/`Operator`/`Engineer`/`""` = nie) | `Operator` | ta sama macierz uprawnień co reszta panelu |
| wymuszenie ze Studia | — | zawsze TAK | zasady wymuszeń: Engineer, dziennik, wygasanie, widoczne na panelu; bit WY nigdy |
| REST / MQTT / Home Assistant | `remote_write` | `false` | „HA to okno, nie mózg” — zapis z zewnątrz tylko tam, gdzie projektant pozwolił; poziom osoby (token) nie niższy niż `panel_level` |

Każdy zapis spoza logiki i każda odmowa trafia do dziennika audytowego:
`INTERNAL_BIT_WRITTEN` / `INTERNAL_BIT_WRITE_REFUSED` — kto (`PANEL:Operator`,
`REST:Engineer`, `MQTT:Kowalski`), skąd, kiedy, stara i nowa wartość.
Bit wymuszony należy do wymuszającego: zapis z panelu/zdalny jest
odrzucany do zdjęcia wymuszenia.

REST: `POST /api/v1/bits/M.<nazwa>` `{"value": true}` (Bearer token).
MQTT: `{"action": "bit", "target": "M.<nazwa>", "values": {"value": true}}`
w kopercie komend (`core/remote_commands.py`).

## Zezwolenie aparatu — blokada twarda

Rejestr aparatów: pole **Zezwolenie** = bit WY (BOOL) logiki. Żądanie →
CommandManager → logika sprawdza zezwolenie → ACCEPTED albo REJECTED
z powodem nazywającym bit i jego opis:

```
ZAMKNIJ KOT_KMG1 odrzucone: brak zezwolenia M.KMG1_ZEZW (Blokada od Q1 otwartego)
```

Trzy warunki (każdy ma test w `runtime/epw_os/tests/test_internal_bits_io.py`):

- **(a)** zezwolenie blokuje TYLKO ZAMKNIJ/ZAŁĄCZ (`CLOSE`). OTWÓRZ/WYŁĄCZ
  nigdy nie jest blokowane przez bit logiki.
- **(b)** logika zatrzymana, bit nieznany, bit nie-WY, sterownik przed
  pierwszym skanem, brak programu → zezwolenie = FALSE. Powód dopisany
  do odmowy („— logika zatrzymana”, „— sterownik przed pierwszym skanem”…).
- **(c)** blokada dotyczy toru komend programowych. Wyjścia pisane przez
  skan i żądania zabezpieczeniowe (`REQ.PROT.*`, blok rejestrów ADA01)
  nie przechodzą przez bramkę; tor zabezpieczeniowy ADA01 idzie własną
  drogą do cewki.

„Sprawdź projekt”: zezwolenie musi być bitem BOOL o kierunku WY z
rejestru (inaczej błąd — sterownik potraktowałby to jako „nigdy”);
zezwolenie na aparacie innym niż SWITCHED to ostrzeżenie.
