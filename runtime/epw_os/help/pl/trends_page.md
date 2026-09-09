# Strona Trendy

Historian zapisuje historię wartości każdego tagu od zawsze, ale dopóki
nie powstała ta strona, jedynym sposobem, żeby ją zobaczyć, był eksport
do CSV i otwarcie go gdzie indziej. Trendy pozwalają obejrzeć przebieg
wartości w czasie — albo obserwować ją na żywo — bez wychodzenia z
programu. Dostępne na każdym poziomie dostępu: to podgląd, nie
sterowanie.

## Dwa tryby

**Historia** — wybierz zakres dat i godzin Od/Do i kliknij **Wczytaj**.
Pickery pokazują czas lokalny Twojego komputera; Historian przechowuje
czas w UTC wewnętrznie, a konwersja odbywa się automatycznie (dokładnie
ta sama konwersja, z której korzysta już okno eksportu danych
historycznych).

**Na żywo** — przesuwające się okno czasowe (1 min / 5 min / 15 min /
1 godz.), które stale przewija się do przodu, z nowymi punktami
dopisywanymi w miarę napływania. Nie ma zakresu dat do ustawienia.

## Wybór tagów

Zaznacz maksymalnie **5 tagów** jednocześnie z listy po lewej (każdy
tag, dla którego Historian kiedykolwiek cokolwiek zapisał). Pięć,
ponieważ dokładnie tyle kolorów system motywów wizualnych gwarantuje
jako wizualnie rozróżnialne od siebie *w każdym z pięciu motywów* —
6. przebieg wymagałby koloru bez takiej gwarancji.

## Osie

Tagi o różnych jednostkach inżynierskich dostają automatycznie osobne
osie pionowe — narysowanie napięcia i prądu na jednej osi spłaszczyłoby
prąd do płaskiej linii blisko zera. Maksymalnie **4 osie**
jednocześnie (przy limicie 5 tagów pokrywa to każdy realistyczny
przypadek bez zagracania wykresu). Tag typu bool (wejście/wyjście
cyfrowe) zawsze dostaje własny rodzaj osi, ustaloną na 0/1, rysowaną
schodkowo — sygnał faktycznie zmienia stan skokowo, nie stopniowo, więc
linia nie ma się między wartościami pochylać.

## Odczyt wykresu

- **Kółko myszy**: powiększanie/pomniejszanie, wyśrodkowane na
  kursorze.
- **Kliknij i przeciągnij**: przesuwanie w poziomie wzdłuż osi czasu.
- **Najechanie kursorem**: celownik pokazuje czas i wartość każdego
  widocznego przebiegu w tym miejscu.
- **Pełny widok**: powrót do całego wczytanego zakresu (Historia) albo
  całego aktualnego okna (Na żywo).
- Skala pionowa każdej osi automatycznie dopasowuje się do tego, co
  aktualnie widać — powiększ pozornie płaski fragment, a skala
  przeliczy się, żeby pokazać rzeczywisty szczegół.

## Dane symulowane

Przebieg dla tagu bez rzeczywistego czujnika/miernika za sobą (patrz
[Co zapisuje Historian](help://hist_what)) jest rysowany **linią
przerywaną**, z dopiskiem "(symulowane)" w legendzie — to samo
oznaczenie SIMULATED używane wszędzie indziej w programie, nie osobna
konwencja tylko dla tej strony.

## Duży zakres nie zawiesza programu

Zakres kilku dni to mogą być setki tysięcy wierszy w bazie danych.
Wczytywanie działa w osobnym wątku — interfejs pozostaje responsywny, a
w trakcie pracy widać komunikat "Wczytywanie...". Przed narysowaniem
dane są ograniczane do w przybliżeniu tylu punktów, ile wykres faktycznie
może pokazać przy swojej bieżącej szerokości — same wartości nadal są
pobierane z bazy (nic spoza żądanego zakresu czasu i listy tagów nigdy
nie jest odczytywane), po prostu nie wszystkie są indywidualnie
rysowane.

## Eksport

**Eksportuj widoczny zakres...** otwiera to samo okno eksportu CSV co
**Narzędzia → Eksportuj dane historyczne...**, już ustawione na
aktualne okno czasowe wykresu i zaznaczone tagi — patrz
[Eksport danych historycznych](help://hist_export), co zawiera plik
CSV.
