# Czym jest program logiki

Ten sterownik nie tylko pokazuje i zapisuje — **wykonuje program
sterowania**. Program to schemat blokowy zbudowany w Logic Studio, tam
skompilowany i przewożony w `projekt.epw`. Nie ma osobnego pliku do
wgrywania.

## Skan

Program pracuje w pętli, na własnym wątku: odczytaj wszystkie wejścia,
których używa, policz wszystkie bloki, zapisz wszystkie prowadzone
wyjścia. Jedno przejście to **skan**. Pasek stanu pokazuje, ile trwa —
patrz [Wskaźnik logiki](help://logic_state).

Wyjście bloku może zostać zobaczone przez następny blok w tym samym
skanie tylko wtedy, gdy kompilator mógł je tak uszeregować; tam, gdzie
uniemożliwia to pętla, wartość dociera **o jeden skan później**. To nie
jest usterka — tak działa każdy sterownik cykliczny, a Logic Studio
mówi, których połączeń to dotyczy.

## Co wolno mu prowadzić

Wyjścia, i wyłącznie przez warstwę sterowników — tę samą granicę, przez
którą idzie komenda z tego panelu. Znaczy to, że safety kernel,
[wymuszenie](help://dio_force) trzymane na tym wyjściu i [tryb
szkoleniowy](help://saf_training_mode) obowiązują logikę dokładnie tak
samo jak Ciebie.

Wyjście prowadzone przez logikę jest **zablokowane dla obsługi ręcznej**:
panel odmawia komendy i mówi dlaczego, zamiast walczyć z programem
o to wyjście skan po skanie. Przepuszczenie komendy wstawiłoby Ciebie
i skan w wyścig, który zawsze przegrywasz — następny skan nadpisze ją
po kilku milisekundach, co wygląda dokładnie jak komenda, która „nie
zadziałała".

Blokada obowiązuje **tylko wtedy, gdy skan pracuje**. Zatrzymany program
niczego nie prowadzi, więc obsługa ręczna jest wtedy jedyną obsługą
i panel ją dopuszcza.

## Jeden przypadek, w którym zablokowane jest wszystko

Jeśli ten sterownik miał pracować z programem logiki, a programu nie dało
się wczytać, komendy są odrzucane komunikatem **„Logic Runtime
Unavailable - Commands Blocked (Fail Safe)"**. To nie jest zepsuty panel:
sterownik nie wie, które blokady mają chronić instalację, więc nie
pozwala niczym operować, dopóki się tego nie dowie. Sterownika, któremu
nigdy nie dano logiki, to nie dotyczy — nie ma co do czego mieć
wątpliwości.

## Kiedy program się zatrzymuje

Zatrzymanie skanu sprowadza każde prowadzone przez program wyjście do
**stanu bezpiecznego** — dwustanowe wyłączone, analogowe 0 — i tam je
zostawia. To jest celowe: program policzony do połowy, sterujący
instalacją, jest gorszy niż brak programu.

Dzieje się tak przy zatrzymaniu skanu, przy [przeładowaniu
logiki](help://logic_reload) i w trakcie [przebudowy całego
projektu](help://proj_install).

## Gdy program został odrzucony

Program, którego sterownik nie potrafi wczytać, jest zgłaszany przy
starcie, a sterownik **pracuje bez logiki użytkownika** — nie udaje, że
jest inaczej. Reszta działa bez zmian: ekrany, alarmówka,
zabezpieczenia. Przekompiluj w Logic Studio i wgraj projekt jeszcze raz.
