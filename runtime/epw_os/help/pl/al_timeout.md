# Automatyczne wylogowanie

Po podniesieniu poziomu powyżej User uruchamia się 5-minutowy licznik
bezczynności. Każdy ruch myszą, kliknięcie albo naciśnięcie klawisza
resetuje ten licznik od nowa.

Jeśli przez 5 minut nie będzie żadnej aktywności, program:

1. Automatycznie obniża poziom z powrotem do User.
2. Pokazuje okno z informacją o wygaśnięciu sesji.
3. Przełącza widok z powrotem na Main View.

Jest to niezależne od wygaszania ekranu (patrz
[Wygaszanie ekranu](help://set_screen_sleep)) — to dwa osobne
mechanizmy: jeden dotyczy poziomu dostępu, drugi wyłącznie jasności
ekranu.

**W trybie kiosku ten mechanizm działa dokładnie tak samo** — jeśli
pasek menu został pokazany po wejściu na poziom Engineer, po 5 minutach
bezczynności poziom wraca do User, a pasek menu automatycznie znika.
Sam tryb kiosku pozostaje włączony — automatyczne wylogowanie nigdy nie
wychodzi z kiosku, tylko obniża poziom dostępu.
