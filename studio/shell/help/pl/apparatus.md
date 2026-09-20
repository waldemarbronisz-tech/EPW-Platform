# Rejestr aparatów

Aparat to rzecz, którą operator obsługuje jako całość: wyłącznik,
stycznik, zawór, napęd. Rejestr wiąże ją z surowymi punktami.

| Kolumna | Znaczenie |
|---|---|
| **Id** | oznaczenie, unikalne (np. `Q1`, `KM1`) |
| **Zachowanie** | `SWITCHED` (łączeniowy), `SIGNAL` (sygnalizacja), `MEASURED` (pomiar), `MODULATED` (regulacja), `SELECTOR` (przełącznik) |
| **Rodzaj** | typ katalogowy — wyłącznik, stycznik, zawór… |
| **Potwierdzenie** | punkty, z których czytasz stan; przycisk otwiera listę |
| **Sterowanie** | punkty wyjściowe; ten sam sposób przypisywania |
| **Styl komendy** | jak wygląda impuls — patrz niżej |
| **Impuls** | długość impulsu w ms (dla stylów impulsowych) |

## Style komendy

**MAINTAINED (poziom)** — cewka pod napięciem = załączony (jedna cewka),
albo po jednej cewce na kierunek, trzymanej pod napięciem.

**PULSE (impuls na kierunek)** — osobne cewki, po impulsie na każdy
kierunek. Stan „załączony" istnieje tylko wtedy, gdy jest jedno wyjście.

**PULSE_TOGGLE (przekaźnik bistabilny jednocewkowy)** — **jedna** cewka
klasy R15/3P za jednym albo dwoma wyjściami. Każdy impuls **przerzuca**,
więc sterownik pulsuje tylko wtedy, gdy potwierdzenie mówi, że aparat
nie jest już w żądanym stanie. **Potwierdzenie jest tu obowiązkowe** —
bez znajomości stanu każdy impuls byłby zgadywaniem.

## Co sprawdza [Sprawdź projekt](help://validation)

- aparat wskazujący punkt, którego nie ma w rejestrze;
- aparat wskazujący punkt na karcie, której już nie ma w składzie;
- **punkt przypisany do dwóch aparatów naraz**;
- styl impulsowy z czasem impulsu równym 0;
- `PULSE_TOGGLE` bez potwierdzenia albo z więcej niż dwoma wyjściami.

## Gdzie aparat się potem pojawia

- na [ekranie](help://screens) — symbol wiązany przez `deviceId`;
- w [logice](help://logic) — jako jedna komenda, nie dwa wyjścia;
- w [Teście zabezpieczeń](help://protection_tests) — jako obiekt,
  którego czas sprzężenia można zmierzyć.
