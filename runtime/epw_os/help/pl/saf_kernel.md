# Monitorowanie zdrowia systemu (safety_kernel)

Zgodnie z zasadą [ekran informuje, sprzęt chroni](help://saf_principle),
moduł monitorujący stan zdrowia systemu (safety_kernel) jest
**czujnikiem, a nie zabezpieczeniem**. Sprawdza stan co 1 sekundę, na
osobnym wątku, żeby nie spowalniać sterowania.

## Co wykrywa

Dla każdego skonfigurowanego urządzenia, dowolny z trzech warunków
oznacza "niezdrowy":

- urządzenie nie odpowiedziało w 3 kolejnych cyklach sprawdzania z
  rzędu (pojedynczy zgubiony pakiet to nie awaria — stąd próg trzech,
  nie jednego);
- tagi należące do urządzenia nie odświeżyły się w skonfigurowanym
  czasie;
- wątek sterownika obsługującego urządzenie przestał działać.

Wynik jest wystawiany jako dwa rodzaje tagów dla każdego urządzenia
(oraz zbiorczo dla całego systemu): stan bieżący (zmienia się sam, w
obie strony) i zatrzask awarii (ustawiany przy wykryciu, kasowany
WYŁĄCZNIE przez ręczne potwierdzenie — dokładnie tak, jak opisano w
[Kwitowanie i po co jest](help://alm_ack)). Awaria, która sama ustąpiła,
pozostaje widoczna, dopóki ktoś jej nie potwierdzi.

## Co robi

Wykrycie niezdrowego stanu:

- podnosi alarm na stronie Alarmy (przez ten sam mechanizm alarmowy co
  awaria komunikacji czy EMERGENCY STOP);
- zapisuje zdarzenie do dziennika audytowego;
- **blokuje wydawanie NOWYCH komend sterujących**, dopóki system nie
  wróci do stanu zdrowego — z zapisem tego faktu.

## Czego świadomie NIE robi

Moduł ten **nigdy nie wysyła żadnej komendy do żadnego wyjścia** — nie
otwiera ani nie zamyka aparatów, nie reaguje samodzielnie na wykrytą
awarię. Jedyna jego reakcja to zablokowanie nowych komend i
zasygnalizowanie problemu. Decyzja o tym, co zrobić z wykrytą awarią
(np. bezpieczne wyłączenie danego obwodu), należy do logiki użytkownika
konfigurowanej osobno — w obecnej wersji programu taka logika jeszcze
nie jest wczytywana.
