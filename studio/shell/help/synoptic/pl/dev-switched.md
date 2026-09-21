# 4.4 SWITCHED - sterowalne dwustanowe

SWITCHED to sterowalne urzadzenie dwustanowe: stycznik, zawor, przepustnica. Ma wejscie zwrotne (feedback), wyjscie sterujace (command), nadzor (supervision) i stan bezpieczny (safeState).

## Sprzezenie zwrotne (feedback.mode)

Tryb DUAL uzywa dwoch wejsc cyfrowych (diClosed i diOpen), co pozwala odroznic cztery stany:

| diClosed | diOpen | Znaczenie |
| --- | --- | --- |
| 0 | 1 | Otwarty |
| 1 | 0 | Zamkniety |
| 0 | 0 | W ruchu albo przewod zerwany |
| 1 | 1 | Blad (oba krancowki jednoczesnie) |

Tryb SINGLE uzywa jednego wejscia (diClosed) z opcjonalnym zanegowaniem (invert) i NIE ODROZNIA stanu posredniego ani zaniku sygnalu od stanu OFF - jest to swiadome ograniczenie tego trybu, nie usterka. Tryb NONE nie ma zadnego wejscia zwrotnego: sterowanie dziala w petli otwartej, ekran nigdy nie potwierdzi rzeczywistego stanu aparatu.

## Sterowanie (command)

Liczba wyjsc (1 albo 2) i styl (MAINTAINED, PULSE albo PULSE_TOGGLE) razem opisuja realny uklad:

- 1 wyjscie, MAINTAINED - typowy stycznik/zawor z jedna cewka trzymana pod napieciem w stanie zalaczonym.
- 1 wyjscie, PULSE - krotki impuls na jedna cewke, tylko kierunek ZALACZ (WYLACZ nie jest sterowane stad).
- 2 wyjscia, MAINTAINED - typowy zawor trojpolozeniowy z oddzielnymi cewkami OTWORZ/ZAMKNIJ.
- 2 wyjscia, PULSE - typowy stycznik bistabilny z oddzielnymi impulsami ZALACZ/WYLACZ (dwie cewki).
- 1 albo 2 wyjscia, PULSE_TOGGLE - przekaznik impulsowy JEDNOCEWKOWY (klasa R15/3P): kazdy impuls przelacza ZALACZ<->WYLACZ, niezaleznie od tego, ktore wyjscie (albo lokalny przycisk) go podalo. Runtime podaje impuls tylko wtedy, gdy sprzezenie zwrotne mowi, ze aparat NIE jest juz w zadanym stanie - inaczej przelaczylby go w druga strone. Sprzezenie (SINGLE albo DUAL) jest obowiazkowe.

Przy 2 wyjsciach pole doOpen jest wymagane; przy 1 - zabronione. Przy stylu PULSE i PULSE_TOGGLE pole pulseMs (czas impulsu w milisekundach, > 0) jest wymagane; przy MAINTAINED - zabronione. PULSE_TOGGLE z trybem sprzezenia NONE jest bledem.

## Nadzor i stan bezpieczny

confirmTimeoutMs to czas (co najmniej 100 ms - ponizej tego progu nadzor przestaje miec sens wobec realnego czasu dzialania sprzetu) na potwierdzenie zmiany stanu przez wejscie zwrotne, zanim zglaszany jest alarm rozbieznosci (discrepancyAlarm) - ROZBIEZNOSC to sytuacja, gdy polecenie zostalo wyslane, ale wejscie zwrotne nie potwierdzilo go w tym czasie (PRZEKROCZENIE CZASU to samo zdarzenie nazwane od strony zegara; discrepancyAlarm to, czy w ogole zglaszac to jako alarm). safeState.onStartup i onLinkLoss (NO_CHANGE/OPEN/CLOSE) opisuja, co MA ZROBIC SPRZET w tych sytuacjach - patrz [1.3](help://synoptic/intro-principle).

> **Uwaga:** switchCounter (licznik przelaczen) celowo NIE MA wlasnego progu ostrzegawczego w tym kontrakcie - prog definiuje sie w EPW-Logic-Studio, odczytujac sygnal .COUNTER ([4.9](help://synoptic/dev-signals-commands)). Prog ostrzegawczy wbudowany w konfiguracje sprzetu bylby ukryta logika wewnatrz opisu sprzetu - to swiadoma decyzja projektowa, nie brak funkcji.
