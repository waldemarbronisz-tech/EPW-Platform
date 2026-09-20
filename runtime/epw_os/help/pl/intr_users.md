# Użytkownicy alarmówki

Trzy [poziomy dostępu](help://al_three) nigdy nie umiały odpowiedzieć na
pytanie „tylko Kowalski rozbroi magazyn" — dwóch operatorów to dla nich
ten sam Operator. Użytkownicy imienni umieją.

## Kto istnieje i kto o tym decyduje

**Osoby** pochodzą z projektu: identyfikator, nazwisko, poziom, jaki
daje ich własny kod, i strefy, którymi mogą operować (pusta lista =
wszystkie). To projektuje się w Studiu.

Ich **sekrety** należą do tego sterownika. **Ustawienia → Użytkownicy
alarmówki** (Engineer) to miejsce, w którym:

- **nadajesz kod na klawiaturę** — wpisywany dwa razy, zapisywany
  jednokierunkowo, nie do odczytania z powrotem;
- **kasujesz go** — osoba zostaje, po prostu nie może się zalogować;
- **wydajesz token zdalny** — do sterowania tym sterownikiem przez
  [MQTT](help://mqtt_commands). Pokazuje się **raz**;
- **unieważniasz go** — co nie rusza jej kodu na klawiaturę.

Wydanie nowego tokenu natychmiast zastępuje poprzedni. Tak się załatwia
token, który wyciekł.

## Token to nie kod

Dwa osobne sekrety tej samej osoby. Token leży w automatyzacji Home
Assistanta na innej maszynie; gdyby był tym samym kodem, wyciek stamtąd
otwierałby panel przy szafie. Unieważnienie jednego nie rusza drugiego.

## Co to zmienia w zapisie

Gdy nikt nie jest zalogowany jako osoba, dziennik pisze
„Panel:Operator". Po kodzie osoby pisze jej nazwisko: „Kowalski
rozbroił strefę Hala". Odmowy też — nie ta strefa, konto wyłączone,
nieznany kod — wszystko trafia do dziennika audytowego i do [historii
alarmowej](help://intr_history).

## Dlaczego kodu nie ma w projekcie

`projekt.epw` jedzie do Studia, do repozytorium i po sieci. Kody
i tokeny to sekrety tego jednego sterownika, więc zostają w jego własnym
pliku lokalnym, pod identyfikatorem użytkownika.

Wynika z tego rzecz warta zapamiętania: **osoba istnieje, gdy projekt
wyląduje, a loguje się, gdy ktoś nada jej tutaj kod.**
