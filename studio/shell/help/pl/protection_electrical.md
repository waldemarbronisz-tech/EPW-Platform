# Zabezpieczenia elektryczne

Nastawy funkcji przekaźnikowych ANSI. **Wykonuje je karta ADA01**, nie
program sterownika — tutaj ustala się wartości, z którymi ma pracować.

Po lewej drzewo: kategoria → funkcja → etap. Po prawej konfiguracja
zaznaczonego etapu.

## Kategorie i funkcje

| Kategoria | Funkcje |
|---|---|
| **Napięcie** | 27 podnapięciowe, 59 nadnapięciowe, 59N nadnapięciowe składowej zerowej, 47 kolejność / zanik faz |
| **Częstotliwość** | 81U podczęstotliwościowe, 81O nadczęstotliwościowe |
| **Prąd** | 50 nadprądowe bezzwłoczne, 51 nadprądowe zwłoczne, 46 składowa przeciwna, 49 przeciążenie cieplne, 50N/51N doziemne |
| **Zasilanie** | zanik napięcia sterowania, zanik zasilania technicznego |

Większość funkcji ma **dwa etapy** — zwykle pierwszy jako ostrzeżenie,
drugi jako wyłączenie.

## Pola etapu

| Pole | Znaczenie |
|---|---|
| **Włączony** | czy etap w ogóle pracuje |
| **Wielkość** | co jest mierzone (napięcie, prąd, częstotliwość…) — z katalogu |
| **Nastawa** | próg zadziałania, w jednostce funkcji |
| **Histereza** | o ile musi wrócić, żeby przestało być przekroczone |
| **Zwłoka** | po jakim czasie przekroczenia etap działa (ms) |
| **Akcja** | `Warning` (ostrzeżenie) albo `Trip` (wyłączenie) |

## Skąd biorą się wartości początkowe

Z katalogu ADA01. **Etap, którego projekt nie wymienia, ma wartość
domyślną z katalogu** — brak wpisu nie znaczy „wyłączone", znaczy
„domyślne". Po wysłaniu projektu warto porównać je z rzeczywistością
przez **Nastawy sterownika (na żywo)** w [Połączeniu ze
sterownikiem](help://controller).

Nastawy etapów są **nastawami**, nie strukturą: panel może je zmienić
(z wpisem do dziennika), a Studio zobaczy różnicę — patrz [Zapis,
rewizja i nastawy](help://save_versioning).
