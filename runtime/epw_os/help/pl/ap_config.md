# Konfiguracja: typ sygnału, zakresy, jednostka, miejsca dziesiętne

Pełna konfiguracja otwiera się przyciskiem **Configure** przy wierszu
punktu (Engineer). Opis, jednostka i notatka techniczna NIE są tu już
edytowane — te trzy pola edytuje się bezpośrednio w tabeli (dwuklik),
tak jak opisano w [Nadawanie opisów](help://dio_descriptions) dla
wejść/wyjść cyfrowych.

## Typ sygnału

Cztery opcje do wyboru:

- **4-20mA** — standardowa pętla prądowa
- **0-10V** — standardowe napięcie
- **0-3.3V ADC (raw)** — surowy sygnał z przetwornika A/C
- **Wartość gotowa (bez przeliczania)** — wartość tagu jest już
  wartością inżynierską, bez żadnego przeliczania (to ustawienie
  domyślne dla nowego punktu)

Dla trzech pierwszych typów pole **zakres surowy** wypełnia się
automatycznie typowymi wartościami dla danego sygnału (np. 4–20 dla
pętli prądowej) — można je swobodnie zmienić.

## Zakresy

**Zakres surowy** to zakres wartości fizycznego sygnału (np. 4–20 mA).
**Zakres inżynieryjny** to zakres wartości pokazywanej na ekranie po
przeliczeniu (np. 0–100 °C). Program przelicza liniowo wartość surową
na wartość inżynieryjną między tymi zakresami. Oba zakresy są ukryte i
nieistotne dla typu "Wartość gotowa" — wtedy wyświetlana jest wartość
tagu wprost, bez żadnego przeliczenia.

## Miejsca dziesiętne

Liczba cyfr po przecinku pokazywana w kolumnie Wartość — czysto
kosmetyczne, nie wpływa na dokładność przechowywanych danych.

## Tag / Adres

Widoczny w tym oknie, ale edytowalny wyłącznie przy tworzeniu nowego
punktu — patrz [Dodawanie i usuwanie punktów](help://ap_add_remove).
