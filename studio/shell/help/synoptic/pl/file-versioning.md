# 10.2 Wersjonowanie schematu i migracje

`CURRENT_SCHEMA_VERSION` (w `ProjectSchema.ts`) rosnie wylacznie przy zmianie niezgodnej wstecz - np. przejscie z modelu polaczen opartego na portach na model wezlowy podniosl wersje z 1 na 2. Kazda taka zmiana ma wlasna migracje (`Migrations.ts`), ktora przeksztalca starszy plik do biezacego ksztaltu przy wczytaniu.

Plik z numerem wersji WYZSZYM niz obslugiwany przez biezaca wersje edytora jest odrzucany od razu, z komunikatem bledu - nigdy nie jest wczytywany czesciowo ani "najlepiej jak sie da".
