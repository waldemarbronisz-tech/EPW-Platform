# Zabezpieczenia elektryczne

Klasyczne nastawy w stylu przekaźnikowym: **Voltage** (podnapięciowe/
nadnapięciowe, przepięcie neutralnej, kolejność/zanik faz),
**Frequency** (podczęstotliwościowe/nadczęstotliwościowe), **Current**
(nadprądowe zwłoczne i bezzwłoczne, składowa przeciwna, przeciążenie
cieplne, doziemienie) oraz **Power/Supply** (zanik napięcia
sterowniczego/technicznego/UPS). Każda funkcja ma jeden lub więcej
**stopni**, każdy z własną Nastawą, Histerezą, Zwłoką i Akcją
(Disabled/Information/Warning/Trip/Custom Logic).

Ta strona to **tabela konfiguracji**, nie żywy monitor — kolumny
"Actual Value" i "Status" są dziś miejscem na przyszłość, nie
prawdziwym pomiarem porównywanym z nastawą. Te nastawy mają docelowo
trafiać do i być wykonywane przez dedykowany sprzęt przekaźnika
zabezpieczeniowego (ADA01), niezależnie od tego komputera, tak jak w
prawdziwej rozdzielnicy przekaźniki zabezpieczeniowe działają dalej
nawet gdy komputer nadzorczy przestanie działać. Nic tutaj obecnie nie
odczytuje żywego tagu ani nie steruje żadnym wyjściem.

Edycja dowolnego pola, włączanie/wyłączanie stopnia i reset statystyk
Zadziałania/Wyłączenia wymagają poziomu **Inżyniera**; podgląd tabeli
nie wymaga żadnego konkretnego poziomu.

Wcześniejsze wersje tej strony zawierały też kategorie Environmental
(temperatura szafki/wilgotność/dym/woda/drzwi/wibracje), Communication
(urządzenie offline) oraz System (baza danych/watchdog/zmiana
konfiguracji). Zostały usunięte, nie przeniesione — były tym samym
rodzajem atrapy co kolumna "Actual Value" wyżej, nigdy niepodpięte do
żadnego realnego tagu ani nieewaluowane wobec niego. Elementy
Environmental przypominające progi też się tu nie zmieściły, bo
prawdziwe progi procesowe mają teraz własną stronę, podpiętą do
faktycznie skonfigurowanych punktów analogowych — patrz
[Zabezpieczenia procesowe](help://prot_process).
