"""Generates studio/shell/help/{pl,en}/*.md - task "zrob rowniez dzial
help pelny". Run manually (`python generate_help.py` from this
directory) whenever a topic needs to change; the .md files themselves
are committed and read directly by HelpPanel (project_panels.py) -
Studio never regenerates them at runtime, same "PNGs are the source of
truth, the script is how you change them" convention
studio/shell/icons/generate_icons.py already established.

Every topic here describes STUDIO'S OWN panels - not copied from
runtime/epw_os/help/ (164 real files exist there, but they document a
DIFFERENT program's own GUI screens, e.g. EPW-OS's own DI/DO pages,
its own alarm arming UI - none of that is what appears on screen here).
Where a Studio panel exposes a REAL runtime concept (Alarmówka's
EOL/2EOL, Zabezpieczenia's ANSI functions), the topic says so plainly
and points at the real module (intrusion_manager.py, protection_
manager.py) rather than re-explaining relay theory from scratch.
"""
import os

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

# Each entry: key -> (title_pl, title_en, body_pl, body_en)
TOPICS = {}


def topic(key, title_pl, title_en, body_pl, body_en):
    TOPICS[key] = (title_pl, title_en, body_pl.strip() + "\n", body_en.strip() + "\n")


topic(
    "welcome", "EPW Studio", "EPW Studio",
    """
# EPW Studio

EPW Studio to jedna aplikacja inżynierska do projektowania instalacji
na platformie EPW: schemat synoptyczny, logika sterowania, rejestr
punktów, aparaty, alarmówka, zabezpieczenia i połączenie ze
sterownikiem — wszystko w jednym oknie, jednym drzewie projektu.

**Ekrany (Synoptic Editor) i Logika (Logic Studio) to działy Studio**,
nie osobne programy — dawne samodzielne uruchamianie każdego z osobna
nie jest już używane.

Wybierz temat z listy po lewej, żeby dowiedzieć się więcej o
konkretnym dziale.
""",
    """
# EPW Studio

EPW Studio is a single engineering application for designing EPW
platform installations: synoptic diagram, control logic, point
registry, apparatus, intrusion alarm, protection settings, and the
controller connection — all in one window, one project tree.

**Screens (Synoptic Editor) and Logic (Logic Studio) are departments of
Studio**, not separate programs — launching each one standalone is no
longer how this is used.

Pick a topic from the list on the left to learn more about a specific
department.
""",
)

topic(
    "info", "Informacje o projekcie", "Project Information",
    """
# Informacje o projekcie

Nazwa, autor, opis i wersja bieżącego projektu. Tu też żyje cykl życia
całego pliku `projekt.epw`, oddzielony celowo od stałego paska
Nowy/Otwórz/Zapisz (ten wciąż dotyczy dokumentu aktywnego edytora —
diagramu Logiki albo ekranu Synoptic):

- **Nowy projekt** — zakłada pusty projekt (potwierdzenie, jeśli
  bieżący ma niezapisane zmiany).
- **Otwórz projekt...** / **Zapisz projekt** / **Zapisz projekt jako...**
  — operują na całym pliku `projekt.epw` (karty, punkty, aparaty,
  alarmówka, zabezpieczenia, magistrala Modbus).

Pole **Wersja** rośnie przy każdym zapisie — to ta sama liczba, którą
Studio powinno porównać z rewizją na sterowniku przed wgraniem projektu
(zobacz temat "Połączenie ze sterownikiem").
""",
    """
# Project Information

Name, author, description, and revision of the current project. This is
also where the whole `projekt.epw` file's own lifecycle lives,
deliberately separate from the fixed New/Open/Save toolbar (that one
still means "the active editor's own document" — a Logic diagram or a
Synoptic screen):

- **New Project** — starts a blank project (asks first if the current
  one has unsaved changes).
- **Open Project...** / **Save Project** / **Save Project As...** —
  operate on the whole `projekt.epw` file (cards, points, apparatus,
  intrusion alarm, protection, Modbus bus).

The **Revision** field increases on every save — the same number Studio
should compare against the controller's own revision before uploading a
project (see "Controller Connection").
""",
)

topic(
    "devices", "Skład urządzenia", "Device Composition",
    """
# Skład urządzenia

Rejestr fizycznych modułów wejść/wyjść: ELA (cyfrowe), ADA (analogowe/
zabezpieczenia), EPM i podobne. Dla każdego modułu:

- **Id** — adres logiczny nadany przez Ciebie (np. `ELA1`) — to on
  tworzy prefiks adresów punktów (`ELA1.DI.1`, `ELA1.DI.2`, ...).
- **Model** — opis/oznaczenie fizyczne (np. `ELA01`).
- **Rodzaj** — DI / DO / AI / AO — jaki typ kanałów ma ten moduł.
- **Kanały** — ile kanałów tego rodzaju moduł udostępnia.
- **Adres Modbus** — numer urządzenia (unit id, 1–247) na magistrali
  Modbus, którą sterownik (Orange Pi) rozmawia z modułami.

**Dodanie karty automatycznie tworzy jej punkty** w Rejestrze punktów —
nie wpisujesz ich ręcznie. Zmiana rodzaju/liczby kanałów przelicza je
na nowo, zachowując opisy już wpisane.

Na dole panelu: **Magistrala Modbus** — jedna, wspólna dla wszystkich
modułów: RTU (port szeregowy, prędkość, parzystość) albo TCP (adres
bramki, port). To ustawienie, jak sterownik ma w ogóle mówić z
modułami — dziś zapisywane w projekcie, gotowe na przyszły sterownik
Modbus w runtime (jeszcze nie zaimplementowany).
""",
    """
# Device Composition

The registry of physical I/O modules: ELA (digital), ADA (analog/
protection), EPM and similar. For each module:

- **Id** — the logical address you assign (e.g. `ELA1`) — it becomes
  the prefix for that module's point addresses (`ELA1.DI.1`,
  `ELA1.DI.2`, ...).
- **Model** — the physical description/designation (e.g. `ELA01`).
- **Kind** — DI / DO / AI / AO — which channel type this module has.
- **Channels** — how many channels of that kind the module provides.
- **Modbus Address** — the device's unit id (1–247) on the Modbus bus
  the controller (Orange Pi) uses to talk to the modules.

**Adding a card automatically creates its points** in the Point
Registry — you never type them by hand. Changing the kind/channel count
regenerates them, keeping any descriptions already typed in.

At the bottom of the panel: **Modbus Bus** — one shared setting for
every module: RTU (serial port, baud rate, parity) or TCP (gateway
address, port). This is how the controller talks to the modules at
all — saved in the project today, ready for a future runtime Modbus
driver (not implemented yet).
""",
)

topic(
    "locations", "Lokalizacje", "Locations",
    """
# Lokalizacje

Lista miejsc instalacji (budynki, kotłownie, pomieszczenia) — kod
(tylko litery A–Z i cyfry) i opis. Kod lokalizacji jest prefiksem
identyfikatorów aparatów w całym projekcie (`KOT_KMG1` i `MH_KMG1` to
dwa różne aparaty), więc musi być unikalny.

Lokalizacje przypisujesz punktom w Rejestrze punktów — czysto opisowo,
żeby wiedzieć, gdzie fizycznie jest dany zacisk.
""",
    """
# Locations

The list of installation places (buildings, boiler rooms, rooms) — a
code (letters A–Z and digits only) and a description. A location's code
is the prefix for apparatus ids across the whole project (`KOT_KMG1`
and `MH_KMG1` are two different devices), so it must be unique.

Locations are assigned to points in the Point Registry — purely
descriptive, so you know where a given terminal physically is.
""",
)

topic(
    "points", "Rejestr punktów", "Point Registry",
    """
# Rejestr punktów

Każdy kanał każdej karty ma tu swój wiersz — pusty, dopóki go nie
nazwiesz. Kolumny:

- **Adres** — kartowy, tylko do odczytu (`ELA1.DI.1`).
- **Opis** — nazwa punktu, np. "Wyłącznik główny — załączony".
- **Lokalizacja** — z listy Lokalizacji.
- **Notatka techniczna** — wolny tekst dla serwisanta (zacisk, przewód).
- **Typ sygnału / Raw min/max / Eng min/max / Jednostka / Miejsca
  dziesiętne** — skalowanie, tylko dla punktów analogowych (AI/AO);
  wyszarzone i chowane dla DI/DO przefiltrowanych do jednej karty.
- **Aparat** — tylko do odczytu: który aparat (z Rejestru aparatów)
  już zajął ten punkt, jeśli którykolwiek.

Filtr **Karta** u góry ogranicza widok do jednej karty naraz.
""",
    """
# Point Registry

Every channel of every card gets its own row here — empty until you
name it. Columns:

- **Address** — card-relative, read-only (`ELA1.DI.1`).
- **Description** — the point's name, e.g. "Main breaker — closed".
- **Location** — from the Locations list.
- **Technical Note** — free text for the technician (terminal, cable).
- **Signal Type / Raw Min/Max / Eng Min/Max / Unit / Decimals** —
  scaling, analog points (AI/AO) only; grayed and hidden for DI/DO when
  filtered to one card.
- **Device** — read-only: which apparatus (from the Apparatus
  Registry) already claimed this point, if any.

The **Card** filter at the top narrows the view to one card at a time.
""",
)

topic(
    "apparatus", "Rejestr aparatów", "Apparatus Registry",
    """
# Rejestr aparatów

Aparat (stycznik, zawór, czujnik...) to id, zachowanie (SWITCHED /
SIGNAL / MEASURED / MODULATED / SELECTOR), rodzaj (etykieta opisowa) i
dwie listy punktów: **Odczyt** (feedback) i **Sterowanie** (command).

Przycisk przy każdej liście otwiera okno wyboru punktów — checklistę
wszystkich punktów projektu. **Punkt zajęty już przez inny aparat ma
checkbox wyłączony** i widoczne, który aparat go zajął — to jest realne
wykrywanie konfliktu w momencie przypisania, nie dopiero przy
uruchomieniu instalacji.
""",
    """
# Apparatus Registry

An apparatus (contactor, valve, sensor...) is an id, a behavior
(SWITCHED / SIGNAL / MEASURED / MODULATED / SELECTOR), a kind
(descriptive label), and two point lists: **Feedback** and
**Command**.

The button next to each list opens a point-picker — a checklist of
every point in the project. **A point already claimed by another
apparatus has its checkbox disabled** and shows which apparatus owns
it — a real conflict check at the moment of assignment, not only once
the installation is running.
""",
)

topic(
    "screens", "Schemat synoptyczny", "Synoptic Diagram",
    """
# Schemat synoptyczny

Edytor graficzny ekranów operatorskich (Synoptic Editor), osadzony jako
dział Studio — te same narzędzia rysowania (przewody, ramki, budynki,
media, style linii), wyrównanie, mierniki, panele sygnałowe i grupowe
przyciski poleceń, co w samodzielnym Synoptic Editor, tylko w jednej
szacie graficznej ze wszystkimi innymi działami.

Karty i lokalizacje dodane w "Skład urządzenia"/"Lokalizacje" pojawiają
się też tutaj (i odwrotnie) — jeden wspólny rejestr, nie dwa osobne.
""",
    """
# Synoptic Diagram

The graphical operator-screen editor (Synoptic Editor), embedded as a
Studio department — the same drawing tools (wires, frames, buildings,
media, wire styles), alignment, meters, signal panels, and group
command buttons as the standalone Synoptic Editor, just in one skin
alongside every other department.

Cards and locations added under "Device Composition"/"Locations" show
up here too (and vice versa) — one shared registry, not two separate
ones.
""",
)

topic(
    "logic", "Logika", "Logic",
    """
# Logika

Edytor logiki sterowania (Logic Studio), osadzony jako dział Studio —
biblioteka bloków, symulacja, kompilacja, eksport do runtime — te same
narzędzia co w samodzielnym Logic Studio, w jednej szacie graficznej ze
wszystkimi innymi działami.
""",
    """
# Logic

The control-logic editor (Logic Studio), embedded as a Studio
department — block library, simulation, compilation, export to
runtime — the same tools as the standalone Logic Studio, in one skin
alongside every other department.
""",
)

topic(
    "zones", "Strefy (Alarmówka)", "Zones (Intrusion Alarm)",
    """
# Strefy

Strefa to nazwana grupa linii dozorowych, uzbrajana/rozbrajana jako
jedność, z własnym **czasem na wyjście** i **czasem na wejście** (w
sekundach) — realne pola z modułu alarmówki w runtime.

Sekcja **Nadzór zasilania** (na dole) jest wspólna dla całego systemu,
nie dla pojedynczej strefy: punkt analogowy dla sieci 230V i osobny dla
akumulatora, każdy ze swoim "stan OK = wysoki" (który poziom sygnału
oznacza sprawność).

Strefy z przypisanymi liniami nie da się usunąć — najpierw przepisz
albo usuń jej linie w dziale "Linie dozorowe".
""",
    """
# Zones

A zone is a named group of supervised lines, armed/disarmed as one
unit, with its own **exit delay** and **entry delay** (in seconds) —
real fields from the runtime's intrusion alarm module.

The **Power Supervision** section (at the bottom) is system-wide, not
per-zone: one analog point for mains (230V), a separate one for the
battery, each with its own "OK state = high" (which signal level means
healthy).

A zone with lines still assigned cannot be removed — reassign or
remove its lines in "Supervised Lines" first.
""",
)

topic(
    "lines", "Linie dozorowe (Alarmówka)", "Supervised Lines (Intrusion Alarm)",
    """
# Linie dozorowe

Każda linia to jedno nadzorowane wejście, przypisane do strefy. Tabela
pokazuje Id/Nazwę/Strefę/Typ; przycisk **Konfiguruj...** otwiera pełną
konfigurację:

- **Tryb pracy** — Stykowy (wejście cyfrowe, DI) albo Parametryzowany
  (wejście analogowe, AI, z rezystorem końca linii).
- **Rodzaj rezystora** — **EOL** (pojedynczy) albo **2EOL** (podwójny)
  — tylko w trybie parametryzowanym. 2EOL rozróżnia dodatkowo Zwarcie i
  Sabotaż, EOL tylko Naruszenie/Bezpieczny/Przerwę.
- **Okna wartości** — zakresy Min/Max (w jednostkach inżynierskich) dla
  każdego rozpoznawanego stanu linii.
- **Czas potwierdzenia (czułość)** — jak długo naruszenie musi trwać,
  zanim zostanie policzone (filtr zakłóceń chwilowych).
- **Liczba naruszeń (krotność)** — ile naruszeń w oknie czasowym jest
  wymagane, żeby zadziałać (ustaw na 2, żeby uzyskać "dwukrotność").
- **Blokada po liczbie alarmów** — automatyczna blokada linii po serii
  alarmów w jednym cyklu uzbrojenia.
- **Podtrzymanie alarmu** — po ilu sekundach alarm sam się kasuje
  (0 = trzyma się aż do rozbrojenia).
- **Czas ciszy do podejrzenia awarii** — brak naruszenia przez tyle
  sekund oznacza linię jako podejrzaną (ostrzeżenie, nie alarm).

Typy linii: **Natychmiastowa** (alarmuje tylko gdy strefa uzbrojona),
**Zwłoczna** (uruchamia odliczanie wejścia), **Całodobowa** (alarmuje
zawsze, niezależnie od uzbrojenia), **Dozorowa** (nigdy nie alarmuje,
tylko sygnalizuje).
""",
    """
# Supervised Lines

Each line is one supervised input, assigned to a zone. The table shows
Id/Name/Zone/Type; the **Configure...** button opens the full setup:

- **Input Mode** — Contact (a digital DI input) or Parametrized (an
  analog AI input with an end-of-line resistor).
- **Resistor Type** — **EOL** (single) or **2EOL** (double) —
  parametrized mode only. 2EOL additionally distinguishes Short and
  Tamper; EOL only Violated/Secure/Open Fault.
- **Value Windows** — Min/Max ranges (engineering units) for each
  recognized line state.
- **Confirmation Time (sensitivity)** — how long a violation must
  persist before it counts (filters brief glitches).
- **Violation Count (multiplicity)** — how many violations within the
  time window are required to trip (set to 2 for "double-knock").
- **Lockout After Alarm Count** — auto-locks the line after a run of
  alarms in one arm cycle.
- **Alarm Hold Time** — how many seconds until the alarm auto-clears
  (0 = holds until disarm).
- **Silence Time Before Suspect** — no violation for this long marks
  the line suspect (a warning, not an alarm).

Line types: **Instant** (alarms only while the zone is armed),
**Delayed** (starts the entry countdown), **24-Hour** (always alarms,
regardless of arming), **Supervisory** (never alarms, only signals).
""",
)

topic(
    "protection_electrical", "Zabezpieczenia elektryczne", "Electrical Protection",
    """
# Zabezpieczenia elektryczne

Katalog 12 funkcji zabezpieczeniowych w konwencji ANSI (27, 59, 59N,
47, 81U, 81O, 50, 51, 46, 49, 50N, 51N), w 4 kategoriach: Napięcie,
Częstotliwość, Prąd, Zasilanie. Katalog jest **stały** — to sprzęt
(ADA01) go realizuje, projekt nie wymyśla nowych funkcji.

Drzewo po lewej: zaznacz/odznacz checkbox przy stopniu, żeby go
włączyć/wyłączyć — **to jest przełącznik aktywności**. Kliknięcie
stopnia pokazuje po prawej pełną konfigurację: Nastawę, Histerezę,
Zwłokę i **Typ działania** (Disabled / Information / Warning / Trip /
Custom Logic).

Te nastawy trafiają docelowo do ADA01 — runtime jest tu tylko
narzędziem nastawczym ("ekran informuje, sprzęt chroni").
""",
    """
# Electrical Protection

A catalog of 12 ANSI-coded protection functions (27, 59, 59N, 47, 81U,
81O, 50, 51, 46, 49, 50N, 51N), in 4 categories: Voltage, Frequency,
Current, Power Supply. The catalog is **fixed** — the hardware (ADA01)
implements it, a project doesn't invent new functions.

The tree on the left: check/uncheck a stage's box to enable/disable it
— **that is the activity switch**. Clicking a stage shows its full
configuration on the right: Setting, Hysteresis, Delay, and **Action**
(Disabled / Information / Warning / Trip / Custom Logic).

These settings are ultimately meant for ADA01 — runtime is only a
setting tool here ("the screen informs, the hardware protects").
""",
)

topic(
    "protection_process", "Zabezpieczenia procesowe", "Process Protection",
    """
# Zabezpieczenia procesowe

W przeciwieństwie do elektrycznych, to dynamiczna, tworzona przez
Ciebie lista — dodajesz zabezpieczenie, wybierasz punkt analogowy (z
Rejestru punktów) i ustawiasz **próg górny/dolny**, **histerezę** i
**zwłokę**.

Checkbox "Akt." w tabeli to przełącznik aktywności. Zaznaczona linia
pokazuje po prawej pełną konfigurację. W przeciwieństwie do
elektrycznych, te progi są **oceniane na żywo w runtime**
(process_protection_manager.py), nie tylko wysyłane do sprzętu.
""",
    """
# Process Protection

Unlike Electrical, this is a dynamic, user-created list — add a
protection, pick an analog point (from the Point Registry), and set
its **upper/lower threshold**, **hysteresis**, and **delay**.

The "En." checkbox in the table is the activity switch. The selected
row shows its full configuration on the right. Unlike Electrical, these
thresholds are **evaluated live in runtime**
(process_protection_manager.py), not just downloaded to hardware.
""",
)

topic(
    "controller", "Połączenie ze sterownikiem", "Controller Connection",
    """
# Połączenie ze sterownikiem

Adres (np. `http://192.168.1.50:8000`) i token dostępu do REST API
sterownika EPW-OS — zapisywane lokalnie (nie w pliku projektu, bo token
to sekret operatora, nie dane projektu do współdzielenia).

**Testuj połączenie** i **Pobierz podgląd tagów** są prawdziwe — łączą
się z realnymi punktami `/api/v1/health` i `/api/v1/tags` sterownika.

**Wyślij do urządzenia** i **Zgraj z urządzenia** są celowo uczciwie
niepełne: REST API sterownika **nie ma dziś** żadnego punktu do
wysyłania/pobierania konfiguracji projektu ani sprawdzania rewizji —
kliknięcie pokazuje ten fakt wprost, zamiast udawać, że synchronizacja
się powiodła. To wymaga rozszerzenia po stronie runtime, poza zakresem
Studio.
""",
    """
# Controller Connection

The address (e.g. `http://192.168.1.50:8000`) and access token for the
EPW-OS controller's REST API — stored locally (not in the project
file, since a token is an operator secret, not project data meant to
be shared).

**Test Connection** and **Fetch Tag Preview** are real — they connect
to the controller's actual `/api/v1/health` and `/api/v1/tags`
endpoints.

**Send to Device** and **Receive from Device** are deliberately,
honestly incomplete: the controller's REST API **does not yet have**
any endpoint for uploading/downloading project configuration or
checking a revision — clicking either shows this fact plainly instead
of pretending a sync succeeded. This needs a runtime-side extension,
outside Studio's own scope.
""",
)

for lang_idx, lang in enumerate(("pl", "en")):
    lang_dir = os.path.join(OUT_DIR, lang)
    os.makedirs(lang_dir, exist_ok=True)
    for key, (title_pl, title_en, body_pl, body_en) in TOPICS.items():
        body = body_pl if lang == "pl" else body_en
        with open(os.path.join(lang_dir, f"{key}.md"), "w", encoding="utf-8") as f:
            f.write(body)

# Topic order + titles, read by project_panels.HelpPanel - one shared
# manifest so the generator and the panel never disagree about what
# topics exist or what order they appear in.
manifest_lines = ["# Auto-generated by generate_help.py - do not edit by hand.", "TOPICS = ["]
for key, (title_pl, title_en, _bp, _be) in TOPICS.items():
    manifest_lines.append(f"    ({key!r}, {title_pl!r}, {title_en!r}),")
manifest_lines.append("]")
with open(os.path.join(OUT_DIR, "_manifest.py"), "w", encoding="utf-8") as f:
    f.write("\n".join(manifest_lines) + "\n")

print(f"generated {len(TOPICS)} topics x 2 languages = {len(TOPICS) * 2} files, plus _manifest.py")
