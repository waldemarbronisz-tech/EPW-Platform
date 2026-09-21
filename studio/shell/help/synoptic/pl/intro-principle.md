# 1.3 Zasada nadrzedna: ekran informuje, sprzet chroni

Cala architektura tej platformy trzyma sie jednej zasady: EKRAN INFORMUJE, SPRZET CHRONI. Synoptyka i logika w EPW-Logic-Studio pokazuja operatorowi stan i dostarczaja wygodne, kontekstowe blokady - ale ostateczna ochrona (bezpiecznik, stycznik z wlasna cewka zanikowa, zawor zwrotny) musi istniec fizycznie, niezaleznie od tego, co dzieje sie na ekranie.

W tym edytorze zasada ta widac wprost w kontrakcie aparatu SWITCHED: pole `safeState` (patrz [4.4](help://synoptic/dev-switched)) opisuje, co aparat ma zrobic PRZY STARCIE i PRZY UTRACIE LACZNOSCI - a nie co ma zrobic operator recznie w takiej sytuacji. To sprzet i jego wlasna konfiguracja decyduja o stanie bezpiecznym, nie logika ekranu.

Podobnie: brak wejscia zwrotnego (`feedback.mode` NONE, patrz [4.4](help://synoptic/dev-switched)) oznacza, ze ekran nigdy nie potwierdzi, czy polecenie faktycznie zadzialalo. To swiadomy, dopuszczony wybor konfiguracji - ale konsekwencja jest wprost nazwana w formularzu aparatu, nie ukryta.
