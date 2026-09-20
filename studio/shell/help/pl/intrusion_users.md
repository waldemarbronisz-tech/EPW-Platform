# Użytkownicy alarmówki

Kto wolno uzbrajać i rozbrajać które strefy — imiennie.

Trzy poziomy dostępu (User / Operator / Engineer) nie potrafiły
odpowiedzieć na pytanie „tylko Kowalski rozbroi magazyn": dwóch
operatorów to dla nich ten sam Operator. Ta kartoteka to potrafi.

| Kolumna | Znaczenie |
|---|---|
| **Id** | identyfikator osoby, np. `U1` — pod nim leżą jej sekrety na sterowniku |
| **Nazwisko** | co zobaczysz w dzienniku zamiast „Panel:Operator" |
| **Poziom** | jaki poziom dostępu daje jej własny kod |
| **Strefy** | które może obsługiwać; **pusta lista = wszystkie** |
| **Aktywny** | odznaczenie wyłącza konto, nie kasując go |

## Kodu tu nie ma i nigdy nie będzie

`projekt.epw` jedzie do Studia, do gita i po sieci. Kod na klawiaturę
i token zdalny to sekrety **egzemplarza sterownika** — leżą w jego
własnym pliku dostępu, pod id użytkownika, zapisane jednokierunkowo.

Z tego wynika porządek pracy: **osoba istnieje, gdy projekt wyląduje na
sterowniku, a loguje się, gdy ktoś nada jej kod na panelu**
(Ustawienia → Użytkownicy alarmówki, poziom Engineer). Tam też wydaje
się **token zdalny** dla [MQTT](help://mqtt) — pokazywany raz; token to
nie kod, więc wyciek z Home Assistanta nie otwiera panelu przy szafie.

## Co to zmienia w dzienniku

Dziennik pisze „Kowalski rozbroił strefę Hala", a nie „Panel:Operator".
Odmowa też: nie ta strefa, konto wyłączone, nieznany kod — wszystko
trafia do dziennika i do historii alarmowej.
