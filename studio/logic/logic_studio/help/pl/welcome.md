# Witamy w EPW Logic Studio {version}

EPW Logic Studio to edytor schematów logicznych do projektowania i
symulacji logiki sterowania, eksportowanej następnie do uruchomienia w
EPW-OS. Rysujesz schemat z bloków (wejścia, bramki, timery, przerzutniki,
liczniki, wyjścia), sprawdzasz go w symulacji na tej samej kanwie, a
skompilowany program trafia do sterownika razem z projektem Studia.

Zacznij od [Pierwszego schematu](help:guide_first_diagram), albo od razu
przejrzyj **Katalog bloków** w drzewie po lewej, żeby zobaczyć, co masz
do dyspozycji (np. bramkę [AND](help:block:logic.and)).

Jeśli coś na schemacie wygląda znajomo, ale nie wiesz dokładnie, co
robi — zaznacz to i naciśnij **F1**: pomoc otworzy się od razu na
właściwym opisie.

## Spis treści

- **Pojęcia** — rzeczy, które łatwo pomylić (etykiety kontra znaczniki,
  zaślepka kontra wolny koniec przewodu, opóźnienie o cykl skanu) oraz
  rodziny bloków: [bramki](help:concept_gates), [timery](help:concept_timers),
  [przerzutniki i zbocza](help:concept_memory_edges),
  [liczniki](help:concept_counters).
- **Poradniki** — krok po kroku: pierwszy schemat, przenoszenie
  sygnału, symulacja, eksport, makrobloki, [typowe układy
  sterowania](help:guide_typical_circuits) z gotowymi połączeniami.
- **Katalog bloków** — pełny, zawsze aktualny opis każdego bloku w
  bibliotece: piny, właściwości, wartości domyślne. Strony bramek,
  timerów, przerzutników, zboczy i liczników mają dodatkowo **tabelę
  prawdy**, **animację** ze schematu w symulacji i **przykłady
  zastosowania**.
- **Skróty klawiszowe** — lista aktualnie zarejestrowanych skrótów.

## Jak czytać animacje w Katalogu bloków

Animacja to prawdziwy schemat z tego edytora, przeliczany przez ten sam
silnik, którego używa symulacja: **zielony** przewód i port to TRUE,
**czarny** to FALSE; wejścia DI po lewej przełącza „operator”, wyjście
DO po prawej pokazuje wynik. To dokładnie ten obraz, który zobaczysz na
własnym schemacie po naciśnięciu Start w symulacji.

## Jedna pomoc dla całego Studia

Ten sam zbiór tematów jest dostępny w EPW Studio (F1 w dziale Logika)
obok pomocy Rejestrów, Ekranów i sterownika — odsyłacze między
działami działają w obie strony.
