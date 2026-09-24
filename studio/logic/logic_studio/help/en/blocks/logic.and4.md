The four-input form of [AND](help:block:logic.and): TRUE only when **all
four** inputs are TRUE.

### Example: a switchgear section ready

`Q1 closed` AND `Busbar live` AND `No protection tripped` AND `AUTO mode`
-> `M.SEKCJA_GOTOWA`. An input the site does not have (say, no mode
signal) should be **stubbed**, not left unconnected - an unconnected
input is FALSE, so readiness would never come.
