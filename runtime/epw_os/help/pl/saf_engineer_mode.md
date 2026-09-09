# Engineer Mode (weryfikacja zabezpieczeń)

Strona **Engineer Mode** (panel nawigacji po lewej) to narzędzie
serwisowe do formalnego przetestowania rzeczywistego pobudzenia i
czasu zadziałania danego stopnia zabezpieczenia względem jego nastawy,
z zachowaniem datowanego zapisu wyniku. To inne narzędzie niż strona
Zabezpieczenia elektryczne (patrz
[Zabezpieczenia elektryczne](help://prot_electrical)), która tylko
pokazuje i edytuje nastawy — Engineer Mode faktycznie przeprowadza
test wobec tego, co tam skonfigurowano.

## Zanim test może się zacząć

Program odmawia startu, dopóki wszystkie poniższe warunki nie są
spełnione, i wskazuje, który zawiódł:

- Jesteś na poziomie **Engineer**.
- Napięcie zasilania jest obecne (szyny pod napięciem).
- Testowany fider jest zamknięty (aktywny).
- Żaden inny fider, który test mógłby wyłączyć, nie jest aktualnie
  zamknięty.
- Żadna komenda łączeniowa nie jest w toku.
- Żadne zadziałanie (trip) nie jest aktualnie aktywne nigdzie w
  systemie.
- Komunikacja z urządzeniem działa (online).

## Przeprowadzanie testu

Wybierz stopień zabezpieczenia z listy i kliknij **Start Test**.
Program płynnie zmienia odpowiedni pomiar (napięcie, częstotliwość
albo prąd, zależnie od zabezpieczenia) w kierunku nastawy stopnia,
czeka na rzeczywiste potwierdzenie, że wyjście faktycznie zadziałało, a
następnie automatycznie przywraca symulowaną wartość oraz wcześniejszy
stan fidera.

## Raport

Każdy ukończony test dopisuje się do tabeli pod terminalem: data,
godzina, zabezpieczenie i wynik. Poza tymi kolumnami program
zapamiętuje też nastawioną i zmierzoną wartość pobudzenia oraz
nastawioną i zmierzoną zwłokę zadziałania dla każdego testu — timeout
czekania na potwierdzenie jest zapisywany jako FAIL, a nie zostawiany
niedokończony. Raporty gromadzą się między sesjami; nie ma sposobu na
ich wyczyszczenie z poziomu ekranu.

Podgląd tej strony wymaga poziomu **Engineer** — patrz
[Co wolno na każdym poziomie](help://al_matrix).
