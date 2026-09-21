# EPW Platform

**Ela Power Watch** — otwarta platforma automatyki i wizualizacji dla
instalacji elektrycznych.

Autor: **mgr inż. Waldemar Bronisz**

---

## Dwa programy, nie trzy

Platforma dzieli się według granicy sprzętowej — tak samo, jak każdy
system automatyki przemysłowej.

### `runtime/` — EPW OS

Program, który **wgrywasz na sterownik** (Orange Pi, Raspberry Pi,
mini PC). Chodzi tam całymi miesiącami bez restartu.

Wykonuje program logiki, rysuje ekrany synoptyczne osadzone w
projekcie, prowadzi system alarmowy, rozmawia z kartami wejść i wyjść
przez Modbus RTU, zapisuje historię, zdarzenia i dziennik audytowy.

Konfigurowany **bezpośrednio na panelu dotykowym**, bez podłączania
komputera — to główna cecha odróżniająca platformę od rozwiązań
komercyjnych.

### `studio/` — EPW Studio

Program, który **instalujesz na komputerze**. Służy do projektowania.
**Jedno okno, jedno drzewo projektu**, a w nim wszystkie działy:

- skład urządzenia, karty, lokalizacje, rejestr punktów, aparaty,
- **Schemat synoptyczny** — edytor ekranów (`studio/synoptic/`, React + Konva),
- **Logika** — edytor logiki sterowania (`studio/logic/`, PySide6),
- alarmówka, zabezpieczenia, integracja MQTT, powiązania obiektu,
- połączenie ze sterownikiem: wysyłka projektu, nastawy na żywo,
  wymuszenia, testy zabezpieczeń, kopia zapasowa.

Powłoka spinająca to `studio/shell/`. Ekrany i Logika są **działami
Studia**, nie osobnymi programami — dawne samodzielne uruchamianie
każdego z osobna nadal działa, ale nie jest już drogą główną.

### `shared/` — część wspólna

Format projektu (`projekt.epw`), gramatyka adresów, biblioteka bloków
logiki wraz z silnikiem wykonawczym, katalog sygnałów systemowych,
biblioteka symboli i dokumentacja kontraktów między programami.

---

## Zasada nadrzędna

> **Ekran informuje, sprzęt chroni.**

EPW OS nigdy nie jest wymagany do zadziałania zabezpieczenia. Ochronę
realizują zabezpieczenia elektroenergetyczne i niezależny tor sprzętowy.
Warstwa programowa może paść, a instalacja pozostaje bezpieczna.

---

## Uruchamianie

### EPW Studio (komputer projektanta)

```
pip install -r studio/logic/requirements.txt
python studio/main.py
```

Pierwsze kroki opisuje pomoc w samym Studiu: **Start → Jak powstaje
projekt, krok po kroku** (dwanaście kroków od pustego pliku do
pracującego sterownika).

Dawne, osobne punkty wejścia nadal działają:
`python studio/logic/main.py`, `python studio/synoptic/main.py`.

### EPW OS (sterownik)

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
Pierwsze kroki po montażu: pomoc panelu, **Pierwsze kroki → Nowy
sterownik, krok po kroku**.

---

## Język

Cały produkt jest dwujęzyczny — polski i angielski — i przełącza się w
jednym miejscu: **Ustawienia → Język**, osobno w Studiu i na panelu.
Przełącza się wszystko: powłoka Studia, edytor ekranów, Logic Studio
wraz z **biblioteką bloków** i katalogiem bloków w pomocy, panel
sterownika i obie sekcje pomocy.

Identyfikatory IEC 61131 (`AND`, `TON`, `CTU`, piny `In1`, `Q`, `CV`,
`PT`) celowo **nie są tłumaczone** — schemat, któremu zmieniono nazwy
pinów, przestaje być czytelny dla kogokolwiek, kto zna normę.

---

## Testy

Zestawy uruchamia się **z katalogu głównego repozytorium**, osobno —
`runtime/test_headless.py` sprawdza, że rdzeń sterownika nie wciąga Qt,
więc nie może dzielić procesu z testami GUI:

```
python -m pytest runtime/epw_os/tests runtime/gui_smoke -q
python -m pytest studio shared -q
python -m pytest runtime/test_headless.py -q
```

---

## Sprzęt

| Moduł | Rola | Stan |
|---|---|---|
| **ELA01** | Karta wejść | projekt |
| **ADA01** | Karta wyjść, dodatkowy tor wyłączający | projekt |
| **EPM** | Rejestrator zakłóceń | koncepcja |

Komunikacja: RS-485 / Modbus RTU, wspólna magistrala.

Mapowanie rejestrów Modbus (kanał *n* → adres *n−1*, DI przez FC2, AI
jako 16-bit bez znaku) jest standardem Modbus, **nie potwierdzonym
zachowaniem tych kart** — do sprawdzenia na sprzęcie narzędziem
`runtime/tools/modbus_probe.py`.

Nazwy **ELA** i **ADA** pochodzą od imion córek autora.

---

## Dokumentacja

| Plik | Co opisuje |
|---|---|
| `shared/docs/SPEC_PROJEKT_EPW.md` | kontrakt formatu `projekt.epw` |
| `shared/docs/PROJEKT_EPW_ZADANIA.md` | jak runtime czyta projekt, co zrobione, co zostało |
| `shared/docs/LOGIKA_W_RUNTIME.md` | wykonywanie logiki na sterowniku, sygnały `SYS.*`, `SEC.*` i `REQ.*` |
| `shared/docs/MQTT_STEROWANIE.md` | sterowanie z Home Assistanta, tokeny, granice zaufania |
| `runtime/ORANGE_PI_DEPLOYMENT.md` | wdrożenie na sprzęcie |
| `CHANGELOG.md` | co niesie każde wydanie i czego nadal nie ma |

Pomoc wbudowana jest pełniejsza niż te dokumenty i dwujęzyczna: 27
tematów w Studiu, ponad 90 na panelu sterownika, osobny dział w Logic
Studio z generowanym katalogiem bloków.

---

## Historia

Platforma powstała z trzech osobnych repozytoriów, połączonych
2026-09-09. Pełna historia rozwoju — 121 zmergowanych Pull Requestów
z raportami — pozostaje dostępna w archiwalnych repozytoriach:

- `EPW-OS` — 44 PR-y
- `EPW-Logic-Studio` — 42 PR-y
- `EPW-Synoptic-Editor` — 35 PR-ów

Duże dokumenty w `studio/logic/` (`AUDIT_REPORT.md`, `AUDIT_SWEEP.md`,
`REPORT.md`) pochodzą sprzed scalenia i opisują Logic Studio jako
samodzielny program. Zostają jako historia — stan dzisiejszy opisuje
pomoc wbudowana i `shared/docs/`.

---

## Licencja

Wolne oprogramowanie. Jeśli szukasz sterownika do własnej instalacji
domowej — trafiłeś dobrze.
