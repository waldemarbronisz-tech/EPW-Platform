# 4.5 SIGNAL - tylko sygnalizacyjne

SIGNAL to urzadzenie wylacznie sygnalizacyjne, bez wyjscia sterujacego: lampka, stycznik pomocniczy uzywany jako czujnik, wylacznik krancowy raportujacy stan bez mozliwosci sterowania z ekranu.

Pola: feedback.di (jedno wejscie cyfrowe) z opcjonalnym invert, alarmState (HIGH albo LOW - ktory POZIOM sygnalu liczy sie jako alarmowy) i debounceMs (opoznienie antydrganiowe, >= 0).

W przeciwienstwie do SWITCHED, SIGNAL nie ma zadnego pola command - nie da sie z niego nic wyslac do sprzetu. To celowe: SIGNAL istnieje po to, zeby cos POKAZYWAC, nigdy zeby czyms STEROWAC.
