# Czym jest system alarmowy

To osobna funkcja od strony [Alarmy](help://alm_source). Alarmy tam to
alarmy **procesowe** — awaria komunikacji z urządzeniem, ZATRZYMANIE
AWARYJNE — stany dotyczące samej instalacji, aktywne niezależnie od
jakiegokolwiek "uzbrojenia".

System alarmowy to system sygnalizacji włamania: nadzoruje zestaw
czujek (**linie dozorowe**), pogrupowanych w **strefy**, które się
uzbraja i rozbraja, i wywołuje alarm, gdy linia zostanie naruszona w
niewłaściwych dla jej typu okolicznościach. Nigdy nie steruje syreną,
światłem ani niczego nie wysyła — co ma się stać przy alarmie, w całości
zależy od programu logiki działającego na tagach, które ten system
wystawia (patrz [Sygnały dla logiki](help://intr_tags)).

Dostępny z grupy **SYSTEM ALARMOWY** w menu nawigacyjnym po lewej —
trzy osobne strony, rozdzielone według tego, dla kogo są i jak często
się z nich korzysta:

- **Podgląd** — praca bieżąca: uzbrajanie/rozbrajanie, bypass, pamięć
  alarmu, tryb chodzenia. Żadnych pól konfiguracyjnych. Podgląd
  dostępny dla każdego; uzbrajanie/rozbrajanie wymaga poziomu Operator
  lub wyższego.
- **Historia zdarzeń** — ten sam filtrowany, eksportowalny dziennik
  zdarzeń co dotychczas, teraz jako osobna strona zamiast zakładki.
- **Konfiguracja** — konfiguracja wyłącznie dla instalatora: strefy i
  linie, tryby wejść, filtry fałszywych alarmów, nadzór zasilania,
  retencja historii. Cała strona wymaga poziomu Inżyniera, nie tylko
  poszczególne przyciski na niej.

Każdy inny temat pomocy w tej sekcji nadal opisuje dokładnie, jak
działają strefy/linie/filtry/uzbrajanie — zmieniło się tylko, KTÓRA z
trzech stron obsługuje daną funkcję, nie samo działanie. Stan zbiorczy
systemu widać też zawsze na pasku statusu na dole okna — nie tylko na
tych trzech stronach.
