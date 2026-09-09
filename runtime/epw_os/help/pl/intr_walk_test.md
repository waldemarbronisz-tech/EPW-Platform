# Tryb chodzenia

Sposób na przejście przez obiekt i potwierdzenie, że każda czujka
faktycznie reaguje, bez wywoływania przy tym prawdziwego alarmu.

**Włączenie** — poziom Engineer, przycisk **Tryb chodzenia** na pasku
narzędzi nad listą stref. Wybierz strefę i opcjonalnie czas trwania
(domyślnie 30 minut) — tryb zawsze wyłącza się sam po tym czasie, więc
nie może pozostać włączony przez zapomnienie. Pozostały czas jest
widoczny na bieżąco.

**Podczas działania**, dla tej strefy:
- Naruszenie linii nadal jest rejestrowane i pokazywane na ekranie — w
  oknie widoczna jest lista wszystkich linii tej strefy z informacją,
  czy już zareagowały, a jeśli tak — kiedy.
- **Nigdy nie wywołuje alarmu ani nie zmienia stanu strefy** — cały sens
  tego trybu to sprawdzenie czujek bez budzenia domowników czy
  wywoływania prawdziwej interwencji.
- **Awaria** linii (sabotaż, zwarcie, przerwa, stan nieokreślony) to
  zupełnie inna sprawa — nadal alarmuje normalnie, dokładnie tak, jakby
  tryb chodzenia był wyłączony. Tryb chodzenia wycisza wyłącznie reakcję
  na *naruszenie*, nigdy na awarię — patrz
  [Tryby linii: stykowy vs. parametryzowany](help://intr_input_modes),
  co liczy się jako awaria.

**Wyłączenie** — przycisk Stop (ręcznie) albo upływ skonfigurowanego
czasu (samoczynnie) kończą tryb w ten sam sposób: podsumowaniem, które
linie się potwierdziły, a które milczały przez cały test, więc od razu
wiadomo, co jeszcze wymaga sprawdzenia przed wyjściem. Włączenie,
wyłączenie i samoczynne wygaśnięcie trafiają do dziennika audytowego
oraz do [historii zdarzeń alarmowych](help://intr_history).

Nic w sposobie uzbrajania strefy, typach jej linii ani filtrach
fałszywych alarmów nie zmienia się podczas trybu chodzenia — patrz
[Uzbrajanie, rozbrajanie i czasy](help://intr_arming) oraz
[Filtrowanie fałszywych alarmów](help://intr_filters).
