# EPW Platform

**Ela Power Watch** — otwarta platforma automatyki i wizualizacji dla
instalacji elektrycznych.

Autor: **mgr inż. Waldemar Bronisz**

---

## Dwa programy, nie trzy

Platforma dzieli się według granicy sprzętowej — tak samo, jak każdy
system automatyki przemysłowej.

### `runtime/` — EPW Runtime

Program, który **wgrywasz na sterownik** (Orange Pi, Raspberry Pi,
mini PC). Chodzi tam całymi miesiącami bez restartu.

Wykonuje logikę, renderuje ekrany synoptyczne, obsługuje system
alarmowy, komunikuje się z kartami wejść i wyjść przez Modbus RTU,
zapisuje historię i zdarzenia.

Konfigurowany **bezpośrednio na panelu dotykowym**, bez podłączania
komputera — to główna cecha odróżniająca platformę od rozwiązań
komercyjnych.

### `studio/` — EPW Studio

Program, który **instalujesz na komputerze**. Służy do projektowania.

- `studio/synoptic/` — edytor ekranów synoptycznych (React, Konva)
- `studio/logic/` — edytor logiki sterowania (PySide6)

Studio potrafi uruchomić runtime lokalnie, żeby **przetestować projekt
w symulacji**, zanim trafi na sterownik.

### `shared/` — część wspólna

Format projektu, rejestr aparatów, lista sygnałów, dokumentacja
kontraktów między programami.

---

## Zasada nadrzędna

> **Ekran informuje, sprzęt chroni.**

EPW Runtime nigdy nie jest wymagany do zadziałania zabezpieczenia.
Ochronę realizują zabezpieczenia elektroenergetyczne i niezależny tor
sprzętowy. Warstwa programowa może paść, a instalacja pozostaje
bezpieczna.

---

## Uruchamianie

### Runtime

```
cd runtime
pip install -r requirements.txt
python main.py
```

Tryb kiosku (docelowy na sterowniku):

```
python main.py --kiosk
```

Wdrożenie na Orange Pi opisane w `runtime/ORANGE_PI_DEPLOYMENT.md`.

### Studio — edytor ekranów

```
cd studio/synoptic
npm install
python main.py
```

### Studio — edytor logiki

```
cd studio/logic
pip install -r requirements.txt
python main.py
```

---

## Sprzęt

| Moduł | Rola | Stan |
|---|---|---|
| **ELA01** | Karta wejść | projekt |
| **ADA01** | Karta wyjść, dodatkowy tor wyłączający | projekt |
| **EPM** | Rejestrator zakłóceń | koncepcja |

Komunikacja: RS-485 / Modbus RTU, wspólna magistrala.

Nazwy **ELA** i **ADA** pochodzą od imion córek autora.

---

## Historia

Platforma powstała z trzech osobnych repozytoriów, połączonych
2026-09-09. Pełna historia rozwoju — 121 zmergowanych Pull Requestów
z raportami — pozostaje dostępna w archiwalnych repozytoriach:

- `EPW-OS` — 44 PR-y
- `EPW-Logic-Studio` — 42 PR-y
- `EPW-Synoptic-Editor` — 35 PR-ów

---

## Licencja

Wolne oprogramowanie. Jeśli szukasz sterownika do własnej instalacji
domowej — trafiłeś dobrze.
