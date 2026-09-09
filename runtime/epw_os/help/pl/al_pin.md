# Zmiana poziomu i wprowadzanie PIN-u

Poziom dostępu zmienia się WYŁĄCZNIE przez rozwijany przełącznik na
górnym pasku (obok zegara), pokazujący aktualny poziom. Nigdy nie
pojawia się on sam z siebie w reakcji na próbę zabronionej czynności —
to świadome działanie operatora.

## Podnoszenie poziomu

1. Kliknij przełącznik poziomu na górnym pasku.
2. Wybierz Operator lub Engineer.
3. Jeśli sesja nie jest jeszcze zalogowana na tym poziomie (albo wyższym),
   pojawi się okno z prośbą o PIN.
4. Wpisz PIN i potwierdź. Błędny PIN pokazuje komunikat i pozwala
   spróbować ponownie, bez zamykania okna.

## Zbyt wiele błędnych PIN-ów pod rząd

Po **5 błędnych PIN-ach z rzędu** dla danego poziomu następuje blokada
na **30 sekund** — w tym czasie odrzucany jest nawet poprawny PIN, więc
zgadywanie nigdy nie może w końcu się udać. Blokada dotyczy tylko
danego poziomu (zablokowany PIN Operatora nie wpływa na Engineer) i
znika automatycznie po 30 sekundach; wpisanie poprawnego PIN-u zeruje
licznik błędnych prób. Każda blokada trafia do
[dziennika audytowego](help://ea_audit_log).

## Obniżanie poziomu

Obniżenie poziomu (np. z Engineer na User) **nie wymaga PIN-u** —
rezygnacja z uprawnień, które się już ma, nie musi być niczym
potwierdzana.

## Wpisywanie PIN-u na ekranie dotykowym

Okno PIN-u ma wbudowany klawiszownik numeryczny, widoczny ZAWSZE,
niezależnie od tego, czy ogólny przełącznik klawiatury ekranowej w
Ustawieniach jest włączony czy wyłączony — inaczej niż w pozostałych
oknach programu. Powód: gdyby klawiszownik PIN-u zależał od tego
przełącznika, wyłączenie go na urządzeniu bez fizycznej klawiatury
zablokowałoby możliwość zalogowania się w ogóle — również po to, żeby
przełącznik z powrotem włączyć. Więcej w rozdziale
[Klawiatura pływająca i wbudowana w okno PIN](help://kb_floating_embedded).
