# Menu Plik

Dostępne na każdym poziomie dostępu, bez PIN-u — to operacje na pliku
projektu, nie czynności istotne dla bezpieczeństwa.

- **Nowy** — resetuje do pustego, nowego projektu. Nic nie zapisuje się
  na dysk aż do Zapisu — do tego czasu widnieje jako niezapisany.
- **Otwórz...** — wczytuje wybrany plik projektu, zastępując bieżący.
  Wczytany plik staje się aktywnym projektem (kolejne Zapisy trafiają
  do niego).
- **Zapisz** — zapisuje bieżący projekt do jego aktywnego pliku.
- **Zapisz jako...** — zapisuje bieżący projekt do wybranego pliku, a
  ten plik staje się nowym aktywnym projektem (kolejne Zapisy trafiają
  tam, nie do starego pliku).
- **Eksport...** — zapisuje samodzielną kopię zapasową bieżącego
  projektu do wybranego pliku. W odróżnieniu od Zapisz jako, aktywny
  plik projektu się nie zmienia — dalej pracujesz na tym samym pliku
  co wcześniej.
- **Import...** — wczytuje wybrany plik i od razu zapisuje jego
  zawartość do *bieżącego* aktywnego pliku projektu. W odróżnieniu od
  Otwórz, ścieżka aktywnego pliku się nie przenosi na importowany plik
  — Import nadpisuje projekt, który już był otwarty, w tym samym
  miejscu.

Nowy, Otwórz i Import pytają najpierw o potwierdzenie, jeśli bieżący
projekt ma niezapisane zmiany — przypadkowe kliknięcie nie skasuje
pracy po cichu.

## Ostatnio otwierane

**Projekt → Ostatnio otwierane** pokazuje listę ostatnio otwieranych
plików projektu (przez Otwórz, Zapisz jako, albo poprzednią pozycję z
tej samej listy). Plik, którego już nie ma pod zapisaną ścieżką, jest
pokazany wyszarzony i oznaczony, nie po cichu pomijany. **Wyczyść**
opróżnia listę.

Zobacz też: [Menu Projekt](help://gs_project_menu).
