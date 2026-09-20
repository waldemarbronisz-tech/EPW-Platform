# Obiekt z kilku sterowników

Jeden `projekt.epw` opisuje **jeden** sterownik. Prawdziwa instalacja
bywa większa: dom ze sterownikiem w kotłowni i drugim przy bramie,
zakład z kilkoma szafami. Plik `obiekt.epwsite` spina je w jedną całość.

## Czym jest obiekt

Listą sterowników — nazwa i ścieżka do pliku projektu każdego z nich.
Same projekty zostają osobnymi plikami w swoich folderach; obiekt ich
nie wchłania.

## Menu Plik

| Pozycja | Co robi |
|---|---|
| **Nowy obiekt** | pusty obiekt, pytanie o nazwę |
| **Otwórz obiekt** | wczytuje `obiekt.epwsite` i jego sterowniki |
| **Dodaj sterownik do obiektu** | nowy, pusty projekt jako kolejne urządzenie |
| **Dodaj istniejący projekt** | dołącza `projekt.epw`, który już masz |
| **Zapisz obiekt** | zapisuje **wszystkie** sterowniki naraz |

„Zapisz" z górnego paska zapisuje tylko **aktywny** sterownik.

## Przełączanie

Kliknięcie sterownika na liście przełącza całe drzewo poniżej na jego
projekt. Edytory oddają swoje dokumenty przy przełączeniu — niezapisane
zmiany nie giną, sterownik zostaje czerwony z gwiazdką, dopóki go nie
zapiszesz.

## Usuwanie

**Usuń sterownik z obiektu** wyjmuje go z listy — **plik projektu
zostaje na dysku**. Jeśli ma niezapisane zmiany, Studio zapyta wprost,
czy je porzucić. Obiekt musi mieć co najmniej jeden sterownik.

## Po co to, poza porządkiem

Żeby sterowniki mogły widzieć nawzajem swoje wartości. To robią
[Powiązania obiektu](help://object_links) — punkt jednego sterownika
staje się tagiem `Link.*` u drugiego, przez MQTT.
