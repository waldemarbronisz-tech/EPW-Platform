# Konfiguracja funkcji

**Ustawienia → Konfiguracja funkcji...** (poziom Engineer) włącza i
wyłącza poszczególne funkcje sterownika, osobno dla każdego projektu.
Rozdzielnica potrzebuje Nastaw zabezpieczeń, dom już nie. Szopa w
ogrodzie potrzebuje Systemu alarmowego, szafka w rozdzielni już nie.

**Wyłączenie funkcji ją ZATRZYMUJE — to nie jest to samo, co ukrycie
strony.** Wyłączona funkcja:
- nie uruchamia żadnego wątku w tle ani timera
- nie rejestruje żadnych tagów w TagManager
- nie zapisuje niczego na dysk
- znika całkowicie z drzewa nawigacji

Ma to największe znaczenie na docelowej platformie, Orange Pi
działającym z karty SD — każdy moduł, który nie musi działać, to jeden
wątek mniej, jeden blok pamięci mniej i jedna rzecz mniej zapisująca na
kartę.

**Czego nie da się wyłączyć**: Widok główny (bez niego nie ma z czego
korzystać), Wejścia cyfrowe i Wyjścia sterujące (podstawowe zadanie
sterownika), Alarmy i Rejestr zdarzeń (podstawowa diagnostyka) oraz
Dziennik audytowy — zawsze, bez wyjątku, bo dziennik audytowy, który
dałoby się wyłączyć, sam stałby się sposobem na ukrycie tego, co się
działo, gdy był wyłączony.

**Ponowne włączenie** funkcji uruchamia jej moduł od nowa i od razu
przywraca jej tagi — bez restartu w żadną stronę, okno na chwilę się
przebudowuje w miejscu, tym samym mechanizmem, którego już używa zmiana
języka.

**Przed wyłączeniem** dostajesz ostrzeżenie, jeśli Twój program logiki
odwołuje się do któregoś z tagów tej funkcji, albo jeśli funkcja
produkuje dane (historię alarmową, liczniki łączeń, notatki
serwisowe...), które po prostu przestaną powstawać — wyłączenie mimo to
nadal jest możliwe, ale dopiero po tym ostrzeżeniu, po jawnym
potwierdzeniu.

**Nic z tego, co już zapisane, nigdy nie jest kasowane.** Historia
alarmowa, liczniki łączeń, notatki serwisowe — wszystko zostaje
dokładnie tam, gdzie było. Włącz funkcję z powrotem później, a
wszystko nadal tam jest, z uczciwą dziurą na czas, gdy była wyłączona,
a nie przepisaną historią udającą, że nic się nie stało.

**Tryb inżyniera potrzebuje Nastaw zabezpieczeń (Elektryczne)** — cały
sens Trybu inżyniera to weryfikacja FAKTYCZNIE skonfigurowanych nastaw
zabezpieczeń elektrycznych tego projektu; przy wyłączonych
zabezpieczeniach elektrycznych nie ma czego naprawdę weryfikować,
więc Tryb inżyniera jest niedostępny, dopóki nie zostaną włączone z
powrotem, niezależnie od własnego przełącznika.

**Historia zdarzeń i Konfiguracja (System alarmowy) potrzebują całego
Systemu alarmowego** — obie strony pokazują/edytują te same, żywe
dane systemu alarmowego, więc są niedostępne, dopóki cały System
alarmowy jest wyłączony, niezależnie od własnego przełącznika (ta sama
zależność, co Tryb inżyniera od Nastaw zabezpieczeń wyżej). Podgląd
NIE MA tej zależności osobno — wykorzystuje bezpośrednio przełącznik
Systemu alarmowego, bo to ta sama strona, którą ten przełącznik zawsze
kontrolował.

**Zabezpieczenia procesowe są całkowicie niezależne od Nastaw
zabezpieczeń (Elektryczne)** — to zupełnie inny moduł (własne progi na
punktach analogowych, nie klasyczne nastawy przekaźnikowe, które
dzielą Elektryczne i Tryb inżyniera), więc pozostaje dostępny nawet
przy wyłączonych zabezpieczeniach elektrycznych, i na odwrót.

Konfiguracja jest zapisywana w samym pliku projektu, nie w programie —
przeniesienie projektu na inny komputer przenosi razem z nim jego
konfigurację funkcji. Projekt sprzed wprowadzenia tego ekranu działa
dokładnie tak jak dotychczas: wszystkie funkcje włączone.
