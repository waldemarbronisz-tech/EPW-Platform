# Zapomniany PIN

Jeśli PIN jest odrzucany zaraz po 5 błędnych próbach, to może wcale nie
być zapomniany — zajrzyj najpierw do
[blokady po zbyt wielu błędach](help://al_pin); ona sama znika po 30
sekundach i nie wymaga żadnego z poniższych kroków.

Program nie ma wbudowanej funkcji odzyskiwania PIN-u z poziomu
interfejsu — nie ma opcji "nie pamiętam PIN-u" w oknie logowania.

PIN-y są przechowywane wyłącznie jako skrót (SHA-256), w pliku
`epw_os/config/access.local.json`, poza plikiem projektu. Ten plik jest
tworzony automatycznie przy pierwszym uruchomieniu programu — wtedy też
program losuje PIN-y dla Operatora i Engineera i pokazuje je JEDEN RAZ
w dzienniku startowym (konsoli).

## Co zrobić, gdy PIN zostanie zapomniany

Jedyna droga to dostęp do samego komputera, na którym działa program
(nie z poziomu interfejsu EPW OS):

1. Zamknij program.
2. Usuń plik `epw_os/config/access.local.json`.
3. Uruchom program ponownie — wygeneruje nowe, losowe PIN-y i pokaże je
   w dzienniku startowym.

To odwraca WSZYSTKIE dotychczasowe PIN-y (Operatora i Engineera),
zapisz więc obie nowe wartości od razu. Nie ma sposobu na odzyskanie
poprzedniego, zapomnianego PIN-u — tylko jego zastąpienie nowym.
