### Jak działa

| S1 | R | Q |
|---|---|---|
| 0 | 0 | bez zmian (pamięta) |
| 1 | 0 | **1** |
| 0 | 1 | 0 |
| 1 | 1 | **1** — Set dominuje |

Przerzutnik **pamięta** stan między skanami: krótki impuls na S1 ustawia Q
na stałe, aż przyjdzie R. Gdy S1 i R są aktywne razem, wygrywa S1. Jeśli w
Twoim układzie ma wygrywać STOP, weź [RS](help:block:memory.rs) — to jest
zwykle właściwy wybór dla napędów. Pełny opis: [Przerzutniki i detekcja
zboczy](help:concept_memory_edges).

### 1. Podtrzymanie po impulsie

Przycisk START daje impuls; napęd ma pracować dalej po puszczeniu:
`START` → S1, `STOP` → R, Q → `DO stycznik`. Po zaniku i powrocie
zasilania sterownika przerzutnik startuje z Q = FALSE (bezpiecznie).

### 2. Alarm z pamięcią (latch)

Zadziałanie zabezpieczenia ma być pamiętane do skasowania przez
operatora, nawet gdy przyczyna minęła: `Zabezpieczenie` → S1,
`Kasowanie z panelu (bit WE M.KASUJ)` → R, Q → lampka i syrena.
Set-dominant gwarantuje, że kasowanie nie zadziała, dopóki przyczyna
trwa.

### 3. Tryb pracy

`Przełącz na AUTO` → S1, `Przełącz na RĘCZNY` → R; Q = TRUE oznacza AUTO.
