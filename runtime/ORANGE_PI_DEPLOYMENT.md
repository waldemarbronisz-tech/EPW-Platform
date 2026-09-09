# EPW OS na Orange Pi — wdrożenie jako kiosk

Instrukcja dla osoby, która zna się na sprzęcie i automatyce, ale nie musi
znać się na programowaniu. Zakłada Orange Pi z Armbianem i ekranem
dotykowym podłączonym bezpośrednio (HDMI/DSI), zamontowane w szafce
sterowniczej.

Efekt końcowy: po włączeniu zasilania Orange Pi samo uruchamia EPW OS na
pełnym ekranie, bez paska tytułu ani przycisków systemu Windows-podobnych
("X" do zamknięcia), i **zamknięcie programu wymaga podania PIN-u
inżyniera**.

---

## 1. Wymagania

### Sprzęt

- Orange Pi (dowolny model z Armbianem obsługującym pulpit graficzny,
  np. Orange Pi 3B/5) z ekranem dotykowym.
- Karta SD/eMMC z zainstalowanym **Armbianem** (wydanie z pulpitem,
  nie "minimal/server" — potrzebny jest serwer X/Wayland, na którym
  odpali się aplikacja graficzna).

### Oprogramowanie systemowe

- **Python 3.12** (ta sama wersja, na której testowany jest EPW OS w CI
  — sprawdź: `python3 --version`; jeśli w repozytorium Armbiana jest
  starsza wersja, doinstaluj z PPA/backports zgodnie z dokumentacją
  Armbiana dla danego modelu).
- Pakiety systemowe wymagane przez bibliotekę graficzną PySide6 (Qt).
  To dokładnie ta sama lista, której używa automatyczne testowanie tego
  projektu (`.github/workflows/python-app.yml`) — jeśli tam kiedyś dojdzie
  nowy pakiet, dopisz go i tutaj:

  ```bash
  sudo apt-get update
  sudo apt-get install -y \
      libegl1 libgl1 libxkbcommon-x11-0 libxcb-cursor0 libxcb-icccm4 \
      libxcb-image0 libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 \
      libxcb-render0 libxcb-xinerama0 libxcb-xfixes0 libxcb-shape0 \
      libxcb-shm0 libxcb-sync1 libxcb-xkb1 libxcb1 libx11-xcb1 \
      libdbus-1-3 libfontconfig1 libglib2.0-0
  ```

- `python3-venv` (środowisko wirtualne Pythona) i `git`:

  ```bash
  sudo apt-get install -y python3-venv git
  ```

---

## 2. Instalacja aplikacji

Wykonuj jako zwykły użytkownik (nie root), np. `orangepi`. Poniżej
przykładowa ścieżka `/home/orangepi/EPW-OS` — jeśli wybierzesz inną,
zamień ją konsekwentnie we wszystkich poleceniach niżej, łącznie z
plikiem `.service` w kroku 4.

```bash
cd /home/orangepi
git clone <adres-repozytorium> EPW-OS
cd EPW-OS

# Środowisko wirtualne - izoluje zależności Pythona EPW OS od reszty
# systemu, żeby aktualizacja/instalacja innego oprogramowania na Orange Pi
# nigdy nie nadpisała bibliotek, na których polega EPW OS.
python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

Sprawdzenie, czy wszystko się zainstalowało poprawnie (bez trybu kiosku,
tylko test uruchomienia rdzenia):

```bash
python test_headless.py
```

Powinno zakończyć się liniami `Core started successfully.` i
`Core stopped successfully. Core is Qt-Free.` bez żadnego błędu. Jeśli
pojawi się błąd o brakującej bibliotece systemowej (`ImportError`,
komunikat o `.so`), wróć do kroku 1 i doinstaluj brakujący pakiet apt.

### Pierwsze uruchomienie (na razie NIE jako kiosk, żeby to zobaczyć)

```bash
source venv/bin/activate
python main.py
```

Aplikacja powinna otworzyć się jako zwykłe okno. Zamknij ją normalnie
(przycisk zamknięcia). To jest ten sam program, który działa na
komputerze deweloperskim — na tym etapie zachowuje się identycznie.

Przy pierwszym uruchomieniu w logu (terminal) pojawi się **wygenerowany
losowo PIN Operatora i Inżyniera** (linie `Default Operator PIN: ####` /
`Default Engineer PIN: ####`) — **zapisz PIN Inżyniera w bezpiecznym
miejscu**, będzie potrzebny do zamknięcia kiosku (patrz sekcja 5) i do
wejścia w tryb inżyniera w samej aplikacji. PIN-y można potem zmienić w
aplikacji: menu **Settings → Change PIN...**.

---

## 3. Autostart jako usługa systemd

Autostart to konfiguracja systemu operacyjnego (Armbian/systemd), **nie**
kod aplikacji — poniżej gotowy plik do skopiowania, nic tu nie trzeba
programować.

### 3.1. Utwórz plik usługi

Utwórz plik `/etc/systemd/system/epw-os.service` (wymaga `sudo`):

```bash
sudo nano /etc/systemd/system/epw-os.service
```

Wklej (dostosuj `User=`, `WorkingDirectory=` i `ExecStart=`, jeśli
zainstalowałeś w innej ścieżce/pod innym użytkownikiem niż w przykładzie
z kroku 2):

```ini
[Unit]
Description=EPW OS - Ela Power Watch (kiosk)
After=graphical.target network.target
Wants=graphical.target

[Service]
Type=simple
User=orangepi
WorkingDirectory=/home/orangepi/EPW-OS
Environment=DISPLAY=:0
ExecStart=/home/orangepi/EPW-OS/venv/bin/python /home/orangepi/EPW-OS/main.py --kiosk
Restart=on-failure
RestartSec=5

[Install]
WantedBy=graphical.target
```

Uwagi do powyższego:

- **`--kiosk`** na końcu `ExecStart` to jedyna różnica między zwykłym a
  kioskowym uruchomieniem — to on włącza pełny ekran bez ramki i wymóg
  PIN-u inżyniera przy zamknięciu. Bez tego argumentu program uruchomi
  się jak zwykłe okno (przydatne, gdyby trzeba było to sprawdzić z
  pulpitu bez ustawiania całej usługi).
- `Environment=DISPLAY=:0` zakłada, że pulpit graficzny Armbiana
  uruchamia się na standardowym ekranie `:0` (domyślne w większości
  konfiguracji). Jeśli masz niestandardową konfigurację pulpitu, dostosuj.
- `Restart=on-failure` — jeśli aplikacja padnie z błędem, systemd
  spróbuje ją ponownie uruchomić po 5 sekundach. **Nie** obejmuje to
  zwykłego zamknięcia (patrz sekcja 5) — po autoryzowanym zamknięciu
  usługa się po prostu zatrzyma (celowo — inaczej Engineer nigdy nie
  mógłby wyłączyć kiosku).

### 3.2. Włącz i uruchom usługę

```bash
sudo systemctl daemon-reload
sudo systemctl enable epw-os.service
sudo systemctl start epw-os.service
```

Od tej pory EPW OS uruchamia się automatycznie przy każdym starcie
systemu, na pełnym ekranie, w trybie kiosku.

### 3.3. Sprawdzanie stanu usługi

```bash
sudo systemctl status epw-os.service
```

Logi aplikacji (przydatne przy diagnozowaniu problemów):

```bash
sudo journalctl -u epw-os.service -f
```

(`-f` = na żywo, jak `tail -f`; bez `-f` pokaże historię i zakończy).

---

## 4. Dostęp do systemu, gdy kiosk działa (SSH)

Kiosk zajmuje cały ekran i nie ma paska zadań ani terminala — do wejścia
"pod spód" (diagnostyka, aktualizacja, zmiana konfiguracji) używaj SSH z
innego komputera w tej samej sieci, **nie** próbuj przełączać okien na
samym Orange Pi.

1. Upewnij się, że SSH jest włączone na Orange Pi (domyślnie włączone na
   większości obrazów Armbiana; jeśli nie: `sudo systemctl enable --now ssh`).
2. Znajdź adres IP Orange Pi (np. z panelu routera, albo lokalnie na
   samym urządzeniu przed pierwszym uruchomieniem kiosku: `ip addr`).
3. Z innego komputera w tej samej sieci:

   ```bash
   ssh orangepi@<adres-IP-orange-pi>
   ```

Po zalogowaniu masz pełny dostęp do terminala Orange Pi **niezależnie od
tego, co w danej chwili wyświetla ekran kiosku** — SSH nie przechodzi
przez pulpit graficzny, więc kiosk może dalej sobie działać na ekranie
podczas gdy Ty pracujesz przez SSH.

---

## 5. Wyłączanie trybu kiosku (żeby coś naprawić na miejscu)

Trzy sposoby, od najszybszego do najbardziej trwałego:

### A) Zamknij program z poziomu ekranu dotykowego (na chwilę)

Kliknij gdziekolwiek w oknie, żeby upewnić się, że aplikacja ma fokus,
potem spróbuj zamknąć program (np. z menu **File → Exit**, dostępnego z
górnego paska menu nawet w trybie kiosku). Aplikacja poprosi o **PIN
Inżyniera** — po poprawnym PIN-ie program się zamknie.

Jeśli usługa systemd jest aktywna (`enable`d), **systemd uruchomi ją
ponownie automatycznie** za kilka sekund (chyba że ją wcześniej
zatrzymasz — patrz punkt B). Ten sposób nadaje się do szybkiego
restartu aplikacji, nie do dłuższej pracy serwisowej.

### B) Zatrzymaj usługę przez SSH (na czas naprawy)

Połącz się przez SSH (sekcja 4) i:

```bash
sudo systemctl stop epw-os.service
```

Ekran wróci do pulpitu Armbiana (albo zgaśnie, zależnie od konfiguracji
wygaszacza samego systemu — to osobna sprawa od wygaszania ekranu w
samej aplikacji, patrz `Settings → Wygaszanie ekranu...`). Możesz teraz
uruchomić EPW OS ręcznie, bez `--kiosk`, żeby popracować w normalnym,
okienkowym trybie:

```bash
cd /home/orangepi/EPW-OS
source venv/bin/activate
python main.py
```

Gdy skończysz, zamknij to ręczne uruchomienie zwykłym zamknięciem okna
(bez trybu kiosku zamykanie **nie** wymaga PIN-u — tylko standardowe
potwierdzenie zapisu, jak w wersji deweloperskiej) i wróć do kiosku:

```bash
sudo systemctl start epw-os.service
```

### C) Wyłącz autostart na stałe (żeby kiosk nie startował sam po restarcie)

```bash
sudo systemctl disable epw-os.service
sudo systemctl stop epw-os.service
```

Odwrócenie (powrót do trybu kiosku):

```bash
sudo systemctl enable --now epw-os.service
```

---

## 6. Aktualizacja aplikacji na działającym urządzeniu

Wykonuj przez SSH (sekcja 4), żeby nie przeszkadzać kioskowi w trakcie
(usługa i tak zostanie na chwilę zatrzymana).

```bash
# 1. Zatrzymaj kiosk na czas aktualizacji.
sudo systemctl stop epw-os.service

# 2. Pobierz nową wersję kodu.
cd /home/orangepi/EPW-OS
git pull

# 3. Zaktualizuj zależności Pythona (na wypadek, gdyby coś się zmieniło
#    w requirements.txt).
source venv/bin/activate
pip install -r requirements.txt

# 4. Szybkie sprawdzenie, że rdzeń nadal startuje poprawnie, zanim
#    wrócisz do trybu kiosku.
python test_headless.py

# 5. Wróć do kiosku.
sudo systemctl start epw-os.service
```

Jeśli krok 4 (`test_headless.py`) zgłosi błąd — **nie uruchamiaj kiosku**,
zostań na poprzedniej, działającej wersji (`git log` pokaże poprzednie
commity, `git checkout <poprzedni-commit>` cofnie kod) i zgłoś problem
osobie odpowiedzialnej za rozwój aplikacji.

**Plik `project.json`** (dane konkretnego projektu/podstacji) oraz pliki
w `epw_os/config/` (np. lokalne PIN-y, zapamiętany rozmiar okna) **nie
są częścią repozytorium kodu** — `git pull` ich nie dotyka, aktualizacja
kodu nie kasuje konfiguracji tego konkretnego urządzenia.

---

## 7. Skrót — najważniejsze polecenia

| Co chcesz zrobić | Polecenie |
|---|---|
| Sprawdzić stan kiosku | `sudo systemctl status epw-os.service` |
| Zobaczyć logi na żywo | `sudo journalctl -u epw-os.service -f` |
| Zatrzymać kiosk (naprawa) | `sudo systemctl stop epw-os.service` |
| Uruchomić kiosk z powrotem | `sudo systemctl start epw-os.service` |
| Wyłączyć autostart na stałe | `sudo systemctl disable epw-os.service` |
| Włączyć autostart z powrotem | `sudo systemctl enable --now epw-os.service` |
| Uruchomić ręcznie, bez kiosku | `python main.py` (bez `--kiosk`) |
| Uruchomić ręcznie, jako kiosk | `python main.py --kiosk` |
| Zaktualizować aplikację | patrz sekcja 6 |
