# 4.2 Konwencja nazewnicza

Kazdy aparat ma trzy oddzielne pola tekstowe, kazde z inna rola:

| Pole | Rola | Przyklad |
| --- | --- | --- |
| id | Klucz maszynowy, NIEZMIENNY po utworzeniu | `KOT_KMG1` |
| designation (oznaczenie) | To, co widac na schemacie | `-K1` |
| name (nazwa) | Opis dla czlowieka | "Stycznik grzalki" |

Zasada jest prosta: CZLOWIEK widzi oznaczenie (na symbolu, w tabelach), MASZYNA widzi id (adresy, odwolania z ekranu). Id musi skladac sie z wielkich liter, cyfr i dokladnie jednego podkreslenia, gdzie czesc przed podkresleniem jest kodem zarejestrowanej lokalizacji (`validateDeviceId`) - std. `KOT_KMG1` znaczy "aparat KMG1 w lokalizacji KOT".

Id jest niezmienny, bo jest kluczem: element ekranu wskazuje na aparat WLASNIE po id ([4.1](help://synoptic/dev-why-not-in-screen)), a lokalizacja aparatu jest z niego wyliczana ([3.1](help://synoptic/reg-locations)). Formularz aparatu wprost blokuje edycje pola Id, gdy edytujemy juz istniejacy aparat - jest ono aktywne tylko przy tworzeniu nowego.

Duplikowanie aparatu (przycisk Duplikuj w liscie) czysci WYLACZNIE id i oznaczenie w nowym szkicu - nazwa, rodzaj, zachowanie i cala konfiguracja szczegolowa (np. adresy kanalow) sa przepisywane bez zmian, wiec trzeba je swiadomie poprawic (przynajmniej adresy kanalow, ktore inaczej koliduja z oryginalem).
