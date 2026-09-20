# EPW Studio

EPW Studio to jedna aplikacja inżynierska do projektowania instalacji na
platformie EPW: schemat synoptyczny, logika sterowania, rejestr punktów,
aparaty, alarmówka, zabezpieczenia i połączenie ze sterownikiem —
wszystko w jednym oknie, w jednym drzewie projektu.

**Ekrany (Synoptic Editor) i Logika (Logic Studio) to działy Studia**,
nie osobne programy — dawne samodzielne uruchamianie każdego z osobna
nie jest już używane.

## Jeśli jesteś tu pierwszy raz

Przeczytaj [Jak powstaje projekt, krok po kroku](help://workflow). To
jest cała droga: od pustego pliku do sterownika, który pracuje według
Twojego projektu — dwanaście kroków, każdy z odnośnikiem do działu,
w którym się go robi.

Potem: [Okno Studia](help://window) — drzewo, paski, oznaczenia
niezapisanych zmian, F1.

## Co to jest projekt

Jeden plik `projekt.epw` = jeden sterownik. Jest w nim **wszystko**, co
ten sterownik ma wiedzieć: skład urządzenia, karty, punkty, aparaty,
ekrany, skompilowana logika, alarmówka, zabezpieczenia, ustawienia MQTT.
Sterownik nie potrzebuje niczego poza tym plikiem — patrz
[Zapis, rewizja i nastawy](help://save_versioning).

Czego w projekcie **nie ma** i nigdy nie będzie: haseł, kodów na
klawiaturę i tokenów. To są sekrety egzemplarza sterownika, nie
instalacji — leżą w jego własnych plikach lokalnych, nie jadą do Studia,
do gita ani po sieci.

## Obiekt i urządzenia

Lewa kolumna zaczyna się od LISTY URZĄDZEŃ: obiekt (np. dom, zakład)
i jego sterowniki, każdy jako osobny `projekt.epw` w swoim folderze,
spięte plikiem `obiekt.epwsite`. Kliknięcie sterownika przełącza całe
drzewo poniżej na jego projekt. Szczegóły: [Obiekt z kilku
sterowników](help://site).

Zwykły pojedynczy `projekt.epw` nadal działa jak dotąd — jako obiekt
z jednym sterownikiem.

## Gdzie szukać dalej

- **Projekt** — każdy dział drzewa, pole po polu.
- **Alarmówka**, **Zabezpieczenia**, **Integracja** — moduły, które
  pojawiają się w drzewie tylko wtedy, gdy są w [składzie
  urządzenia](help://devices).
- **Sterownik** — wysyłka projektu, nastawy na żywo, testy, liczniki.
- **Praca z projektem** — sprawdzanie, zapis, wersjonowanie, słownik.
