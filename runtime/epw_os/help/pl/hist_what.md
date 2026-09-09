# Co zapisuje Historian

Historian to usługa działająca w tle, zapisująca **każdą zmianę
wartości dowolnego tagu** (wejścia, wyjścia, punktu analogowego) do
bazy danych, wraz ze znacznikiem czasu i jakością danych. Zapis odbywa
się asynchronicznie — nie spowalnia sterowania ani wizualizacji.

**Weryfikacja techniczna dla dociekliwych**: w bazie danych istnieje
też tabela na historię alarmów, a Historian nasłuchuje odpowiedniego
zdarzenia, żeby ją zapełniać — jednak w obecnej wersji programu nic nie
generuje tego zdarzenia, więc historia samych alarmów (w odróżnieniu od
historii wartości tagów) w praktyce nie jest dziś zapisywana. Aktywne
alarmy nadal widać na bieżąco na stronie Alarmy (patrz
[Skąd się biorą alarmy](help://alm_source)) — nie są one zapisywane do
Historiana.

Dane zapisane przez Historian są dostępne na dwa sposoby: przez eksport
(patrz [Eksport danych historycznych](help://hist_export)) albo na
ekranie bez eksportowania czegokolwiek, na
[stronie Trendy](help://trends_page).

**Wartości symulowane**: kilka tagów (panel pomiarów w Main View —
napięcie/prąd/częstotliwość, oraz suwaki na stronie Power Quality) nie
ma za sobą żadnego fizycznego czujnika — patrz
[Panel pomiarów](help://mv_measurements). Historian nadal je zapisuje
(żeby eksporty i historia były kompletne), ale z jakością **SIMULATED**
zamiast GOOD, więc zawsze da się je odróżnić od prawdziwego odczytu w
kolumnie Quality eksportu.

**Próg zapisu (deadband)**: nie każda pojedyncza zmiana wartości trafia
do bazy. Tag typu REAL/INT jest zapisywany dopiero, gdy zmieni się o
więcej niż próg (rozsądna wartość domyślna, ustawialna per-tag w pliku
projektu), z wymuszonym okresowym zapisem, żeby stabilna wartość też nie
zostawiała dziury w historii. Tagi logiczne/tekstowe (stany przekaźników,
statusy) są zapisywane przy każdej zmianie zawsze — ten mechanizm chroni
nośnik danych (karta SD na docelowym sprzęcie ma ograniczoną trwałość
zapisu) przed wysokoczęstotliwościową, prawie stałą wartością analogową,
a nie po to, żeby przerzedzać cokolwiek, gdzie liczy się każda zmiana.
