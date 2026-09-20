# Wskaźnik logiki

Pasek stanu niesie jedno pole, **Logika**, z czterema możliwymi
odczytami. Najechanie kursorem pokazuje pełne liczby.

| Odczyt | Co znaczy |
|---|---|
| **RUN** | skan pracuje: ile bloków, czas cyklu, ile skanów do tej pory, ostatni i najdłuższy skan w milisekundach, ile wyjść prowadzi logika |
| **STOPPED** | program jest wczytany, ale **skan nie pracuje** — jego blokady nie są liczone, a jego wyjścia zostały sprowadzone do stanu bezpiecznego |
| **FAULT** | program nie pracuje, z podaniem powodu |
| **brak** | ten projekt nie niesie programu logiki; sterownik pracuje bez logiki użytkownika |

## Po co najdłuższy skan

Ostatni skan mówi, co dzieje się teraz; **najdłuższy** mówi, do czego
program jest zdolny pod obciążeniem. Czas cyklu wygodny średnio, ale co
jakiś czas dziesięciokrotnie dłuższy, to program, który kiedyś kogoś
zaskoczy — ta liczba jest po to, żeby nie musiał.

## STOPPED to nie „bezczynny"

To jest odczyt, który warto poznawać z daleka. Program istnieje, schemat
jest dobry, wszystko wygląda na skonfigurowane — i żadna z jego blokad
niczego nie chroni. Wyjścia stoją w stanie bezpiecznym.

Ta sama informacja jest dostępna przez REST i w Studiu, na panelu
[Połączenie ze sterownikiem](help://api_what).
