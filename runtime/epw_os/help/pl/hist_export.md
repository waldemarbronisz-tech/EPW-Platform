# Eksport danych historycznych

Dostępny z menu **Narzędzia → Eksportuj dane historyczne...**, dla
każdego poziomu dostępu.

## Kroki

1. Ustaw zakres dat **Od** i **Do** — kalendarz otwiera się przyciskiem
   przy polu.
2. Domyślnie zaznaczone jest "Wszystkie tagi". Odznacz tę opcję, żeby
   wybrać z listy konkretne tagi do eksportu.
3. Kliknij **Eksportuj** i wskaż plik CSV.

Plik CSV zawiera kolumny: Timestamp, Tag, Value, Quality — czas w
strefie lokalnej komputera (dane w bazie są przechowywane w UTC i
przeliczane na czas lokalny dopiero przy eksporcie). Jeśli w wybranym
zakresie nie ma żadnych danych, program poinformuje o tym zamiast
utworzyć pusty plik.

Jeśli eksportowany zakres zawiera wartości symulowane (Quality =
SIMULATED — patrz [Co zapisuje Historian](help://hist_what)), okno
dialogowe i komunikat końcowy wyraźnie o tym informują, podając ich
liczbę. Sama kolumna Quality pozwala je odfiltrować lub wykluczyć w
dowolnym narzędziu, którym plik CSV zostanie później otwarty.
