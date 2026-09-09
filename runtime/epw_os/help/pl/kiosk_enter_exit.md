# Wejście i wyjście

## Wejście

Tryb kiosku włącza się na dwa sposoby:

1. **Przy starcie programu** — parametrem `--kiosk`
   (`python main.py --kiosk`).
2. **W trakcie pracy** — Ustawienia → Tryb kiosku, dostępne wyłącznie
   dla poziomu Engineer.

Tryb kiosku nie jest zapamiętywany między uruchomieniami — zwykły
restart programu bez parametru `--kiosk` zawsze uruchamia się normalnie.

## Wyjście

Wyjście z trybu kiosku wymaga poziomu **Engineer** i odbywa się
wyłącznie przez PIN — dwuklik, klawisz Esc i F11 są w kiosku celowo
zablokowane, również wtedy, gdy pasek menu jest akurat widoczny na
poziomie Engineer.

Dwie drogi wyjścia:

- **Ustawienia → Tryb kiosku** (ta sama pozycja menu, która służy do
  wejścia) — dostępna dopiero, gdy jest się już Engineerem, więc
  kliknięcie od razu kończy tryb kiosku bez dodatkowego pytania o PIN.
- **Zamknięcie programu** (np. Alt+F4) — program zapyta o PIN
  Engineera, zanim faktycznie się zamknie.

Każda próba wyjścia — udana i nieudana — jest zapisywana do dziennika
audytowego.
