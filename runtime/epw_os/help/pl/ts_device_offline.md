# Urządzenie pokazuje OFFLINE

Panel statusu urządzeń na Main View (patrz
[Panel statusu urządzeń](help://mv_device_status)) pokazuje jeden z
trzech statusów:

- **OFFLINE** — program jeszcze nie nawiązał żadnej komunikacji z tym
  urządzeniem od uruchomienia (stan normalny na samym początku, zanim
  pierwsze dane napłyną).
- **ONLINE** — komunikacja działa prawidłowo.
- **COMM_FAILURE** — komunikacja DZIAŁAŁA, ale została utracona
  (urządzenie przestało odpowiadać w wyznaczonym czasie).

Jeśli status utknął na OFFLINE dłużej, niż powinien, albo przeszedł w
COMM_FAILURE:

1. Sprawdź panel Alarmy — awaria komunikacji urządzenia podnosi tam
   osobny alarm z nazwą urządzenia.
2. W trybie symulacji (bez podłączonego sprzętu) urządzenia są
   symulowane programowo i status powinien szybko przejść na ONLINE
   sam z siebie — długo utrzymujący się OFFLINE w tym trybie może
   oznaczać, że program dopiero się uruchamia.
3. W trybie live sprawdź fizyczne połączenie z danym urządzeniem.

Zobacz też: [Skąd się biorą alarmy](help://alm_source).
