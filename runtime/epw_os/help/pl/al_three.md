# Trzy poziomy: User, Operator, Engineer

EPW OS ma trzy poziomy dostępu, uporządkowane od najniższego:

1. **User** — poziom domyślny po każdym uruchomieniu programu. Wyłącznie
   podgląd, bez PIN-u.
2. **Operator** — wymaga PIN-u. Pozwala sterować aparatami z Main View.
3. **Engineer** — wymaga PIN-u (innego niż Operator). Pełny dostęp,
   łącznie z konfiguracją i nastawami.

Poziomy są kumulatywne: Engineer ma wszystko, co Operator, a Operator —
wszystko, co User. Program **zawsze** startuje na poziomie User,
niezależnie od tego, na jakim poziomie zakończyła się poprzednia sesja —
sesja nie jest zapamiętywana między uruchomieniami (PIN-y owszem, ale
to inna rzecz — patrz [Zmiana PIN-u](help://al_change_pin)).

Pełna lista tego, co wolno na każdym poziomie: [tabela uprawnień](help://al_matrix).
