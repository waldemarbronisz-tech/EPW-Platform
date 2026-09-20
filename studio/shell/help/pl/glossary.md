# Słownik pojęć

**Adres** — `id_karty.RODZAJ.numer`, np. `ELA1.DI.1`. Jedyny sposób
wskazania kanału w całej platformie.

**Aparat** — rzecz obsługiwana jako całość (wyłącznik, stycznik, zawór),
związana z punktami potwierdzenia i sterowania. Patrz
[Rejestr aparatów](help://apparatus).

**Bit retencyjny** (`MR.` / `MWR.`) — bit wewnętrzny logiki, który
przeżywa restart sterownika.

**Karta** — fizyczny moduł wejść/wyjść. Patrz [Karty](help://io_cards).

**Linia dozorowa** — jedna czujka alarmówki na jednym punkcie. Patrz
[Linie](help://lines).

**Lokalizacja** — kod miejsca, dziedziczony z karty na punkty. Patrz
[Lokalizacje](help://locations).

**Nastawa** — wartość, którą wolno zmienić na panelu. Przeciwieństwo
struktury. Patrz [Zapis i rewizja](help://save_versioning).

**Obiekt** (`obiekt.epwsite`) — kilka sterowników jako jedna instalacja.
Patrz [Obiekt](help://site).

**Odcisk nastaw** (settings hash) — skrót wszystkich nastaw, używany do
wykrycia rozjazdu ze sterownikiem.

**Punkt** — jeden kanał karty, z opisem, lokalizacją i (dla analogowych)
skalowaniem. Patrz [Rejestr punktów](help://points).

**Rewizja** — licznik zapisów projektu.

**Skład urządzenia** — z jakich modułów składa się sterownik. Patrz
[Skład](help://devices).

**Strefa** — kawałek obiektu uzbrajany jako całość. Patrz
[Strefy](help://zones).

**`SSWIN.*`** — sygnały alarmówki dostępne w logice: uzbrojenie, alarm,
pamięć, sabotaż, sygnalizator, komendy.

**`SYS.*`** — sygnały systemowe sterownika dostępne w logice.

**Tag** — nazwana wartość w sterowniku. Adres punktu jest tagiem;
`Security.*`, `Process.*`, `Link.*`, `System.*` też.

**Tryb „Na żywo"** — pokazywanie prawdziwych wartości ze sterownika
w tabelach i w edytorze ekranów.

**Wymuszenie** — przypięcie tagu do wartości przez serwisanta. Wymaga
Engineera, jest w dzienniku, nie przeżywa restartu ani przeładowania
projektu. Patrz [Rejestr punktów](help://points).
