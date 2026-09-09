# Sterowanie aparatami i wymagane uprawnienia

Sterowanie z Main View wymaga poziomu **Operator**.

## Przebieg sterowania

1. Kliknij aparat na schemacie (Q1, KMG, KM1 lub KM2).
2. Pojawia się okno z aktualnym stanem aparatu oraz wierszem
   **Interlock** — informacją, czy komenda przeciwna do bieżącego stanu
   jest dopuszczona. Jeśli logika programu blokuje komendę, przycisk
   odpowiedniej akcji (OTWÓRZ/ZAMKNIJ) jest nieaktywny, a powód
   wypisany wprost.
3. Wybierz OTWÓRZ albo ZAMKNIJ (dostępna jest tylko akcja przeciwna do
   bieżącego stanu).
4. Pojawia się okno potwierdzenia — dopiero jego zatwierdzenie
   faktycznie wysyła komendę. Uprawnienia są sprawdzane ponownie w tym
   momencie, na wypadek gdyby wygasły w czasie, gdy okna były otwarte.
5. Aparat pokazuje stan "w trakcie", a po chwili — stan sprzężenia
   zwrotnego.

## Co blokuje sterowanie

Zanim komenda zostanie wysłana, program sprawdza kolejno:

- czy nie jest aktywny EMERGENCY STOP;
- czy docelowe urządzenie nie jest w stanie awarii komunikacji;
- czy ogólny stan zdrowia systemu jest prawidłowy — patrz
  [Monitorowanie zdrowia systemu](help://saf_kernel);
- reguły logiki sterowania (jeśli projekt logiki jest wczytany).

Jeśli w projekcie nie skonfigurowano żadnej logiki sterowania, jest to
stan normalny — sterowanie ręczne pozostaje dozwolone. Dopiero
skonfigurowana, ale niedziałająca logika blokuje komendy jako
rzeczywistą awarię.
