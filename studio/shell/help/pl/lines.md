# Linie dozorowe

Każda linia to jedno nadzorowane wejście, przypisane do strefy. Tabela
pokazuje Id/Nazwę/Strefę/Typ; przycisk **Konfiguruj...** otwiera pełną
konfigurację:

- **Tryb pracy** — Stykowy (wejście cyfrowe, DI) albo Parametryzowany
  (wejście analogowe, AI, z rezystorem końca linii).
- **Rodzaj rezystora** — **EOL** (pojedynczy) albo **2EOL** (podwójny)
  — tylko w trybie parametryzowanym. 2EOL rozróżnia dodatkowo Zwarcie i
  Sabotaż, EOL tylko Naruszenie/Bezpieczny/Przerwę.
- **Okna wartości** — zakresy Min/Max (w jednostkach inżynierskich) dla
  każdego rozpoznawanego stanu linii.
- **Czas potwierdzenia (czułość)** — jak długo naruszenie musi trwać,
  zanim zostanie policzone (filtr zakłóceń chwilowych).
- **Liczba naruszeń (krotność)** — ile naruszeń w oknie czasowym jest
  wymagane, żeby zadziałać (ustaw na 2, żeby uzyskać "dwukrotność").
- **Blokada po liczbie alarmów** — automatyczna blokada linii po serii
  alarmów w jednym cyklu uzbrojenia.
- **Podtrzymanie alarmu** — po ilu sekundach alarm sam się kasuje
  (0 = trzyma się aż do rozbrojenia).
- **Czas ciszy do podejrzenia awarii** — brak naruszenia przez tyle
  sekund oznacza linię jako podejrzaną (ostrzeżenie, nie alarm).

Typy linii: **Natychmiastowa** (alarmuje tylko gdy strefa uzbrojona),
**Zwłoczna** (uruchamia odliczanie wejścia), **Całodobowa** (alarmuje
zawsze, niezależnie od uzbrojenia), **Dozorowa** (nigdy nie alarmuje,
tylko sygnalizuje).
