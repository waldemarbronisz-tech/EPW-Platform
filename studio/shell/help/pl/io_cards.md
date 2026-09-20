# Karty wejść/wyjść

Fizyczne moduły tego sterownika — i **jedyne** miejsce, w którym
powstają punkty.

## Wiersz = jeden moduł

| Kolumna | Znaczenie |
|---|---|
| **Id** | pierwszy człon każdego adresu tej karty (`ELA1` → `ELA1.DI.1`). Bez kropki i bez spacji |
| **Model** | katalogowy typ modułu |
| **Kanały (rodzaj i liczba)** | zaznaczasz rodzaje, które karta ma, i wpisujesz liczbę kanałów każdego |
| **Adres Modbus** | 1–247, unikalny w projekcie; puste = moduł nie jest jeszcze zaadresowany i **nie odpowiada na magistrali** |
| **Lokalizacja** | gdzie stoi; dziedziczą ją wszystkie jej punkty |
| **Odpowiada** | tylko w trybie „Na żywo": czy sterownik ma z niej odczyt |

Karta z **DI i AI** to **jeden wiersz z dwoma zaznaczeniami**, nie dwa
wiersze. Jeden fizyczny moduł ma jeden adres i jedną lokalizację, więc
dzielenie go na dwa wiersze zmuszałoby do wpisywania tego dwa razy.

## Rodzaje kanałów

`DI` wejścia dwustanowe, `DO` wyjścia dwustanowe, `AI` wejścia
analogowe, `AO` wyjścia analogowe. Adres ma postać `id.RODZAJ.numer`,
bez zer wiodących.

## Co się dzieje po dodaniu karty

Punkty powstają natychmiast w [Rejestrze punktów](help://points).
**Zmniejszenie liczby kanałów usuwa nadmiarowe punkty razem z ich
opisami** — z ostrzeżeniem. Usunięcie karty usuwa wszystkie jej punkty.

Na sterowniku dzieje się to samo przy [przeładowaniu
projektu](help://controller): karta skasowana w Studiu zabiera swoje
tagi.

## Magistrala Modbus

Pod tabelą: **Transport** (RTU po porcie szeregowym albo TCP), a do tego
port i prędkość oraz parzystość dla RTU, albo adres bramy i port TCP.

To jest ustawienie **projektu**. To, który sterownik fizycznie używa
Modbusa, a który symulatora, jest ustawieniem lokalnym sterownika —
widać je w [Połączeniu ze sterownikiem](help://controller).

## Lokalizacje

Przyciski **Dodaj lokalizację** / **Usuń lokalizację** prowadzą do tej
samej listy co dział [Lokalizacje](help://locations) — są tutaj, bo
lokalizacja jest polem karty i najczęściej brakuje jej właśnie w tym
momencie.
