# Zapis, rewizja i nastawy

## Trzy pliki sterownika

| Plik | Co w nim jest | Kto pisze |
|---|---|---|
| `projekt.epw` | projekt: karty, punkty, aparaty, skład, ekrany, logika, alarmówka, zabezpieczenia | Studio; sterownik tylko nastawy |
| `runtime_state.json` | stan: liczniki, uzbrojenie, wykluczenia, pamięć alarmu | wyłącznie sterownik |
| pliki lokalne sterownika | kody, tokeny, hasła, język, REST, retencje | wyłącznie sterownik |

Sekrety nie są w projekcie **nigdy** — projekt jedzie do Studia, do gita
i po sieci.

## Rewizja

Rośnie przy każdym zapisie i niesie informację, **kto zapisał**: Studio
albo panel. Dzięki temu przy wysyłce da się rozpoznać, że sterownik ma
nowszą wersję niż ta, z której wychodzisz — i **zatrzymać się** zamiast
nadpisać cudzą zmianę.

## Struktura kontra nastawa

To jest podział, który decyduje, co wolno zmienić przy szafie:

**Struktura** — co w ogóle istnieje: karty, punkty, aparaty, skład,
strefy, linie, ekrany, logika. Projektuje się to **wyłącznie w Studiu**.
Panel odmawia zmiany struktury i zapisuje tę odmowę w dzienniku.

**Nastawa** — wartość czegoś, co istnieje: czasy strefy, progi
zabezpieczeń, filtry linii, skalowanie punktu analogowego, MQTT,
sygnalizator. Panel może je zmienić (z wpisem do dziennika i rewizją
„panel"), a Studio widzi różnicę i może je przyjąć — patrz [Połączenie
ze sterownikiem](help://controller).

**Odcisk nastaw** (settings hash) to skrót wszystkich nastaw naraz.
Studio porównuje go przed wysłaniem, żeby nie pytać o różnice, których
nie ma.

## Co się zapisuje razem z projektem

Ekran z [edytora ekranów](help://screens) i **skompilowana**
[logika](help://logic). Jeśli logika się nie kompiluje, Studio mówi to
wprost i zostawia poprzednią skompilowaną wersję; jeśli edytor ekranów
odmówi wydania dokumentu, zapyta, czy zapisać projekt z **poprzednio**
zapisanymi ekranami.

## Kopia i wycofanie

Instalacja na sterowniku zostawia poprzedni plik jako `projekt.epw.bak`.
Jeśli nowy okaże się nie do wczytania przy starcie, poprzedni wraca sam,
a odrzucony zostaje do obejrzenia.
