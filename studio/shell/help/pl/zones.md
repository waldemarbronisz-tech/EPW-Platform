# Strefy

Strefa to kawałek obiektu uzbrajany i rozbrajany jako całość: parter,
hala, garaż. Każda [linia dozorowa](help://lines) należy do jednej
strefy.

| Kolumna | Znaczenie |
|---|---|
| **Id** | unikalne, np. `Z1` — pod tym identyfikatorem strefa występuje w tagach i w logice |
| **Nazwa** | czytelna, ta widnieje na panelu |
| **Czas na wyjście (s)** | ile masz na opuszczenie strefy po uzbrojeniu |
| **Czas na wejście (s)** | ile masz na rozbrojenie po naruszeniu linii zwłocznej |

Strefy, do której są przypisane linie, **nie da się usunąć** — najpierw
przepnij albo usuń jej linie.

## Nadzór zasilania

Dwa niezależne, opcjonalne sprawdzenia: **Sieć (230 V)** i **Akumulator**,
każde wskazujące punkt i to, czy stan „w porządku" jest wysoki.

Konwencja platformy: **sprawny sygnał czyta się jako wysoki**, żeby
przerwany przewód albo martwy moduł spadał w dół i wyglądał jak awaria,
a nie jak stan normalny. Nieskonfigurowane sprawdzenie zawsze czyta się
jako sprawne — „brak konfiguracji = brak nadzoru", bez błędów.

## Sygnalizator

Tu są **nastawy**, nie wyjście. Sterownik nie steruje żadną syreną —
wystawia stan (`SEC.SYSTEM.SIREN_ACTIVE`, `SIREN_TIME_LEFT`,
`STROBE_ACTIVE`, `PANIC`), a wyjście podpinasz w [Logice](help://logic),
przez takie blokady, jakich wymaga instalacja.

| Nastawa | Znaczenie |
|---|---|
| **Sygnalizuj najdłużej** | po tym czasie `SIREN_ACTIVE` gaśnie samo, choć alarm trwa dalej; `0` = bez ograniczenia |
| **Linia napadowa nie uruchamia syreny** | domyślnie zaznaczone — patrz typ [Napadowa](help://lines) |

Lampa (`STROBE_ACTIVE`) przeżywa dźwięk: świeci od alarmu aż do
skasowania pamięci alarmu, żeby wracający na obiekt człowiek zobaczył,
że coś się wydarzyło.
