# Zmiana PIN-u

Okno **Ustawienia → Zmień PIN...** ma dwie osobne sekcje — jedną dla
PIN-u Operatora, drugą dla PIN-u Engineera. Obie działają identycznie i
niezależnie.

## Warunek zmiany

Żeby zmienić PIN danego poziomu, trzeba znać **aktualny PIN tego
poziomu** — nie ma znaczenia, na jakim poziomie jest aktualnie
zalogowana sesja. Oznacza to, że:

- osoba zalogowana jako Engineer może zmienić PIN Operatora, ale
  wyłącznie znając stary PIN Operatora;
- samo bycie zalogowanym jako Engineer nie wystarczy, żeby zmienić PIN
  Engineera bez znajomości starego PIN-u.

## Kroki

1. Otwórz Ustawienia → Zmień PIN...
2. W odpowiedniej sekcji wpisz stary PIN, nowy PIN i potwierdzenie
   nowego PIN-u.
3. Kliknij Zapisz.

Nowy PIN musi składać się wyłącznie z cyfr i różnić się od starego.
Zmiana jest zapisywana natychmiast, bez potrzeby zapisywania projektu.

## Gdzie są przechowywane PIN-y

PIN-y nigdy nie są zapisywane jawnym tekstem — program przechowuje
wyłącznie ich skrót (SHA-256), w osobnym pliku poza projektem. Więcej w
rozdziale [Zapomniany PIN](help://ts_forgot_pin).
