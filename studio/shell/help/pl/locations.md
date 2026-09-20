# Lokalizacje

Miejsca, do których odnoszą się karty i punkty: szafa, kotłownia, brama,
hala.

| Kolumna | Zasada |
|---|---|
| **Kod** | krótki, tylko **litery A–Z i cyfry**, unikalny (np. `KOT`, `BRAMA1`) |
| **Opis** | pełna nazwa, którą czyta człowiek |

## Dziedziczenie

Karta stoi w jednej lokalizacji. **Każdy jej punkt dziedziczy tę
lokalizację**, dopóki nie nadasz mu własnej w [Rejestrze
punktów](help://points) — rejestr pokazuje wtedy „(dziedziczona: …)".

Dzięki temu przeniesienie karty do innej szafy to jedna zmiana, a nie
trzydzieści dwie.

## Po co to jest naprawdę

Ta informacja jedzie na sterownik i ląduje przy tagu. Serwisant przy
szafie widzi nie tylko „ELA1.DI.7 — czujka hali", ale też gdzie ten
zacisk fizycznie jest. Bez lokalizacji zostaje pytanie, na które nikt
nie umie odpowiedzieć po dwóch latach.

Punkt wskazujący lokalizację, której nie ma na liście, zgłasza [Sprawdź
projekt](help://validation).
