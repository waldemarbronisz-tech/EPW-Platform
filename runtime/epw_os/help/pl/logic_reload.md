# Przeładowanie programu logiki

**Projekt → Przeładuj program logiki...**, poziom Engineer, z wpisem do
dziennika.

Czyta logikę z pliku projektu na dysku i wprowadza ją do skanu, **bez
restartu sterownika**.

## Co się naprawdę dzieje

1. Pracujący skan zostaje **zatrzymany**, co sprowadza każde prowadzone
   przez niego wyjście do stanu bezpiecznego (dwustanowe wyłączone,
   analogowe 0).
2. Nowy program jest czytany i sprawdzany.
3. Skan rusza na nim od nowa.

Między krokiem 1 a 3 blokady z tego programu niczego nie chronią. Dlatego
panel najpierw pyta, zamiast po prostu to zrobić — przerwanie żywych
blokad musi być Twoją decyzją, a nie niespodzianką.

## Czego nie robi

**Tylko program.** Karty, punkty, aparaty, ekrany i alarmówka nie są
przez tę komendę czytane na nowo. Żeby wprowadzić do pracy cały nowy
projekt, użyj **Plik → Otwórz** — patrz [Wgranie
projektu](help://proj_install), które przebudowuje to wszystko w miejscu
i przeładowuje logikę jako ostatni krok.

## Gdy nowy program zostanie odrzucony

Sterownik mówi to wprost, z powodem, i zostaje **bez logiki
użytkownika** — nie z programem wprowadzonym do połowy. Poprzedni program
nie wraca: został zatrzymany w kroku 1, a ciche cofnięcie się do niego
znaczyłoby, że panel pokazuje jedno, a instalacja robi drugie.

Przekompiluj w Logic Studio, wgraj projekt jeszcze raz i przeładuj.
