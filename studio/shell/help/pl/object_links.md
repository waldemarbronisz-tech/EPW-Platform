# Powiązania obiektu

Obiekt składa się z kilku sterowników, a jeden czasem potrzebuje stanu
z drugiego: brama wjazdowa ma wiedzieć, że dom jest uzbrojony, kotłownia
— że garaż zgłasza zalanie. Powiązanie to para: **punkt źródła** na
jednym sterowniku i **tag `Link.<Id>.In<n>`** na drugim.

Mechanizm to MQTT, który oba sterowniki i tak mają: źródło publikuje
swoje tagi pod `<prefiks>/tag/<ścieżka>/state`, a cel ma w Integracji
MQTT mapowanie przychodzące, które taki temat zamienia w lokalny tag
`Link.*`. Studio wpisuje te mapowania samo (w Integracji MQTT są szare,
z opisem skąd pochodzą; ręcznych mapowań nie dotyka), włącza MQTT i
nadaje prefiks tematów tam, gdzie ich nie było. Broker jest wspólny —
adres wpisujesz w Integracji MQTT każdego sterownika.

Tag `Link.*` u celu jest **informacją, nigdy komendą**: logika może go
czytać, ekran może pokazać symbol związany z nim, ale nic przez niego
nie steruje drugim sterownikiem. Gdy źródło milknie dłużej niż
„ważność", tag u celu dostaje jakość STALE.

Powiązania należą do pliku obiektu; „Zapisz obiekt" zapisuje je razem
z projektami, w których Studio zmieniło Integrację MQTT. Usunięcie
sterownika z obiektu usuwa jego powiązania w obie strony.
