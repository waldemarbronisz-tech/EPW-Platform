"""Generates studio/shell/help/{pl,en}/*.md and _manifest.py - task
"zrob rowniez dzial help pelny", extended 2026-09-20 on the owner's
instruction: "rozbuduj dzial pomoc bo jest strasznie ubogi, rozpisz
wszystkie funkcje jak sie programuje krok po kroku".

Run manually (`python generate_help.py` from this directory) whenever a
topic needs to change; the .md files themselves are committed and read
directly by HelpPanel (project_panels.py) - Studio never regenerates
them at runtime, same "PNGs are the source of truth, the script is how
you change them" convention studio/shell/icons/generate_icons.py already
established. Both languages live in ONE call per topic here, which is
the reason the generator exists at all: a topic cannot be added,
renamed or reordered in one language and forgotten in the other.

Every topic describes STUDIO'S OWN panels - not copied from
runtime/epw_os/help/ (83 files there, documenting a DIFFERENT program's
screens: EPW-OS's own DI/DO pages, its arming UI). Where a Studio panel
exposes a REAL runtime concept (EOL/2EOL, ANSI functions, the sounder),
the topic says so plainly and points at the real module
(intrusion_manager.py, process_protection_manager.py) rather than
re-explaining relay theory from scratch.

Cross-references are written as [text](help://key) - HelpPanel resolves
them itself and never opens a browser (the same scheme EPW-OS's own
help_window.py uses). Curly braces are reserved: load_help_topic_
markdown() runs str.format() on the text, so "{version}" is substituted
and any other brace would break the topic.
"""
import os

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

# Chapters, in the order HelpPanel shows them. A topic names one of
# these keys; a chapter with no topics simply does not appear.
CHAPTERS = [
    ("start", "Start", "Getting started"),
    ("project", "Projekt", "The project"),
    ("alarm", "Alarmówka", "Intrusion alarm"),
    ("protection", "Zabezpieczenia", "Protection"),
    ("integration", "Integracja", "Integration"),
    ("controller", "Sterownik", "The controller"),
    ("working", "Praca z projektem", "Working with a project"),
    ("about_chapter", "O programie", "About"),
]

# key -> (chapter, title_pl, title_en, body_pl, body_en), insertion order
TOPICS = {}


def topic(key, chapter, title_pl, title_en, body_pl, body_en):
    assert chapter in dict((c[0], c) for c in CHAPTERS), chapter
    TOPICS[key] = (chapter, title_pl, title_en, body_pl.strip() + "\n", body_en.strip() + "\n")


# =====================================================================
# START
# =====================================================================

topic(
    "welcome", "start", "EPW Studio", "EPW Studio",
    """
# EPW Studio

EPW Studio to jedna aplikacja inżynierska do projektowania instalacji na
platformie EPW: schemat synoptyczny, logika sterowania, rejestr punktów,
aparaty, alarmówka, zabezpieczenia i połączenie ze sterownikiem —
wszystko w jednym oknie, w jednym drzewie projektu.

**Ekrany (Synoptic Editor) i Logika (Logic Studio) to działy Studia**,
nie osobne programy — dawne samodzielne uruchamianie każdego z osobna
nie jest już używane.

## Jeśli jesteś tu pierwszy raz

Przeczytaj [Jak powstaje projekt, krok po kroku](help://workflow). To
jest cała droga: od pustego pliku do sterownika, który pracuje według
Twojego projektu — dwanaście kroków, każdy z odnośnikiem do działu,
w którym się go robi.

Potem: [Okno Studia](help://window) — drzewo, paski, oznaczenia
niezapisanych zmian, F1.

## Co to jest projekt

Jeden plik `projekt.epw` = jeden sterownik. Jest w nim **wszystko**, co
ten sterownik ma wiedzieć: skład urządzenia, karty, punkty, aparaty,
ekrany, skompilowana logika, alarmówka, zabezpieczenia, ustawienia MQTT.
Sterownik nie potrzebuje niczego poza tym plikiem — patrz
[Zapis, rewizja i nastawy](help://save_versioning).

Czego w projekcie **nie ma** i nigdy nie będzie: haseł, kodów na
klawiaturę i tokenów. To są sekrety egzemplarza sterownika, nie
instalacji — leżą w jego własnych plikach lokalnych, nie jadą do Studia,
do gita ani po sieci.

## Obiekt i urządzenia

Lewa kolumna zaczyna się od LISTY URZĄDZEŃ: obiekt (np. dom, zakład)
i jego sterowniki, każdy jako osobny `projekt.epw` w swoim folderze,
spięte plikiem `obiekt.epwsite`. Kliknięcie sterownika przełącza całe
drzewo poniżej na jego projekt. Szczegóły: [Obiekt z kilku
sterowników](help://site).

Zwykły pojedynczy `projekt.epw` nadal działa jak dotąd — jako obiekt
z jednym sterownikiem.

## Jedna pomoc dla całego Studia

Ta lista obejmuje działy Studia, a pod nimi dwa edytory:
[Ekrany](help://synoptic/intro-what) (edytor synoptyki, rozdziały 1–13)
i [Logikę](help://logic/welcome) (edytor logiki: pojęcia, poradniki,
katalog bloków, skróty). Wszystko w jednym języku — tym, który wybrałeś
w Ustawieniach — i powiązane odnośnikami. **F1** w dowolnym miejscu
otwiera tę pomoc na temacie, w którym stoisz: w dziale Studia na jego
temacie, w edytorze logiki na zaznaczonym bloku, w edytorze ekranów na
zaznaczonym symbolu. Pole nad listą przeszukuje wszystkie tematy naraz.

## Gdzie szukać dalej

- **Projekt** — każdy dział drzewa, pole po polu.
- **Alarmówka**, **Zabezpieczenia**, **Integracja** — moduły, które
  pojawiają się w drzewie tylko wtedy, gdy są w [składzie
  urządzenia](help://devices).
- **Sterownik** — wysyłka projektu, nastawy na żywo, testy, liczniki.
- **Praca z projektem** — sprawdzanie, zapis, wersjonowanie, słownik.
""",
    """
# EPW Studio

EPW Studio is a single engineering application for designing EPW
platform installations: synoptic diagram, control logic, point registry,
apparatus, intrusion alarm, protection settings and the controller
connection — all in one window, one project tree.

**Screens (Synoptic Editor) and Logic (Logic Studio) are departments of
Studio**, not separate programs — launching each one standalone is no
longer how this is used.

## If this is your first time here

Read [How a project is built, step by step](help://workflow). That is
the whole road: from an empty file to a controller running your project
— twelve steps, each linking to the department where you do it.

Then: [The Studio window](help://window) — the tree, the toolbars, how
unsaved edits are marked, F1.

## What a project is

One `projekt.epw` file = one controller. It holds **everything** that
controller needs to know: the device composition, cards, points,
apparatus, screens, the compiled logic, the intrusion alarm, protection
settings, MQTT. The controller needs nothing else — see [Saving,
revisions and settings](help://save_versioning).

What a project never holds: passwords, keypad codes and tokens. Those
are secrets of one controller, not of the installation — they live in
its own local files and never travel to Studio, into git or over the
network.

## Object and devices

The left column starts with the DEVICE LIST: an object (a house, a
plant) and its controllers, each its own `projekt.epw` in its own
folder, tied together by an `obiekt.epwsite` file. Clicking a controller
switches the whole tree below to its project. Details: [An object of
several controllers](help://site).

A plain single `projekt.epw` still works as before — as a
one-controller object.

## One help for the whole Studio

This list covers Studio's own departments and, under them, the two
editors: [Screens](help://synoptic/intro-what) (the synoptic editor,
chapters 1–13) and [Logic](help://logic/welcome) (the logic editor:
concepts, guides, the block catalog, shortcuts). All of it in one
language — the one chosen in Settings — and cross-linked. **F1**
anywhere opens this help on the topic you are in: a Studio department
on its topic, the logic editor on the selected block, the screen editor
on the selected symbol. The box above the list searches every topic at
once.

## Where to look next

- **The project** — every branch of the tree, field by field.
- **Intrusion alarm**, **Protection**, **Integration** — modules that
  appear in the tree only when they are in the [device
  composition](help://devices).
- **The controller** — sending the project, live settings, tests,
  counters.
- **Working with a project** — checking, saving, versioning, glossary.
""",
)

topic(
    "workflow", "start",
    "Jak powstaje projekt, krok po kroku", "How a project is built, step by step",
    """
# Jak powstaje projekt, krok po kroku

Kolejność nie jest dowolna: każdy krok korzysta z tego, co powstało
w poprzednim. **Karty rodzą punkty**, punkty są adresami dla aparatów,
linii dozorowych, zabezpieczeń, ekranów i logiki. Jeśli zaczniesz od
rysowania ekranu, nie będzie do czego przypiąć symboli.

Kroki 1–4 potrafi za Ciebie przeprowadzić [Kreator
urządzenia](help://wizard) (Plik → Kreator urządzenia). Reszta to
normalna praca w drzewie.

---

## Krok 1. Nowy projekt i jego informacje

Górny pasek → **Nowy**, potem dział [Informacje o
projekcie](help://info): nazwa (to ją sterownik podaje jako swój
projekt), autor, opis.

Nazwa korzenia drzewa to ta sama nazwa — dwuklik zmienia ją w miejscu.

## Krok 2. Skład urządzenia

[Skład urządzenia](help://devices) — zaznaczasz, jakie moduły ten
sterownik **ma**. Moduł spoza składu nie istnieje: jego gałąź w drzewie
się nie pokazuje, a w sterowniku nie powstaje ani obiekt, ani wątek, ani
tagi.

Zrób to przed konfiguracją, żeby nie wypełniać działów, których i tak
nie będzie.

## Krok 3. Lokalizacje

[Lokalizacje](help://locations) — krótkie kody miejsc (szafa, kotłownia,
brama). Karta stoi w jednej lokalizacji, a każdy jej punkt dziedziczy ją
domyślnie. Bez tego później nie da się odpowiedzieć na pytanie „gdzie
jest ten zacisk".

## Krok 4. Karty wejść/wyjść i magistrala

[Karty wejść/wyjść](help://io_cards) — jeden wiersz na jeden fizyczny
moduł: id (pierwszy człon każdego adresu), model, jakie ma rodzaje
kanałów i po ile, adres Modbus, lokalizacja.

**To jest moment, w którym powstają punkty.** Karta `ELA1` z 32 kanałami
DI tworzy `ELA1.DI.1` … `ELA1.DI.32` w rejestrze punktów, automatycznie.

Tu też ustawiasz samą magistralę (RTU albo TCP, port, prędkość,
parzystość).

## Krok 5. Opis punktów

[Rejestr punktów](help://points) — każdemu kanałowi piszesz, **co jest
do niego podłączone**, notatkę techniczną i ewentualnie inną lokalizację
niż dziedziczona po karcie. Dla punktów analogowych: typ sygnału,
przeliczenie surowej wartości na wielkość inżynierską, jednostkę
i liczbę miejsc po przecinku.

Ten opis jedzie na sterownik i widzi go operator przy szafie. Adres bez
opisu to numer kanału i nic więcej.

## Krok 6. Aparaty

[Rejestr aparatów](help://apparatus) — wyłącznik, stycznik, zawór:
zachowanie, punkty potwierdzenia i punkty sterujące, styl komendy
(MAINTAINED / PULSE / PULSE_TOGGLE).

Aparat jest tym, co operator naciska na ekranie i co pojawia się
w logice jako jedna rzecz, a nie jako dwa surowe wyjścia.

## Krok 7. Ekran synoptyczny

[Schemat synoptyczny](help://screens) — rysujesz obiekt i wiążesz
symbole z aparatami i punktami. Ekran jest zapisany **w projekcie**,
więc sterownik rysuje dokładnie to, co narysowałeś, bez osobnego pliku.

Tu też umieszczasz wizualizację pomiarów — wskaźniki, zbiorniki,
wartości liczbowe związane z realnymi punktami.

## Krok 8. Logika

[Logika](help://logic) — schemat blokowy na tych samych adresach.
Wejścia, bramki, przerzutniki, czasy, bloki analogowe, sygnały systemowe
`SYS.*` i alarmówki `SSWIN.*`, wyjścia.

Tu zamykasz wszystko, czego sterownik nie robi sam z siebie: np. sygnał
`SSWIN.SIREN_ACTIVE` na wyjście, do którego fizycznie wisi syrena.

## Krok 9. Alarmówka (jeśli jest w składzie)

Po kolei: [Strefy](help://zones) → [Linie dozorowe](help://lines) →
[Użytkownicy](help://intrusion_users). Linia potrzebuje strefy, a
użytkownik potrzebuje stref, którymi ma prawo operować.

W Strefach są też nadzór zasilania i nastawy sygnalizatora.

## Krok 10. Zabezpieczenia (jeśli są w składzie)

[Zabezpieczenia elektryczne](help://protection_electrical) — nastawy
funkcji ANSI wykonywane przez kartę ADA01.
[Zabezpieczenia procesowe](help://protection_process) — progi górny
i dolny na punktach analogowych, oceniane w sterowniku.

## Krok 11. Sprawdź i zapisz

[Sprawdź projekt](help://validation) znajduje rozjazdy, których nie
widać w tabelach: aparat wskazujący nieistniejący punkt, punkt przypisany
do dwóch aparatów naraz, linię bez punktu, moduł z danymi poza składem.

Potem **Zapisz**. Dopiero zapisany plik da się wysłać — sterownik
dostaje plik z dysku, nie zawartość okna.

## Krok 12. Wyślij na sterownik

[Połączenie ze sterownikiem](help://controller) — adres, token Engineer,
**Wyślij na urządzenie**. Studio najpierw porównuje rewizje i nastawy:
jeśli ktoś zmienił coś na panelu, zobaczysz tabelę różnic, zanim
cokolwiek nadpiszesz.

Sterownik **przebudowuje się według nowego projektu bez restartu** —
karty, punkty, aparaty, komendy, alarmówka, logika i panel. Na tej samej
stronie sprawdzisz potem [stan logiki](help://controller), nastawy na
żywo i liczniki.

---

## Co jeszcze warto zrobić

- [Integracja MQTT](help://mqtt) — jeśli sterownik ma rozmawiać z Home
  Assistantem.
- [Powiązania obiektu](help://object_links) — jeśli sterowniki mają
  widzieć nawzajem swoje wartości.
- [Test zabezpieczeń](help://protection_tests) — po uruchomieniu, jako
  dowód, że zabezpieczenie zadziałało w zmierzonym czasie.
""",
    """
# How a project is built, step by step

The order is not arbitrary: each step uses what the previous one
created. **Cards give birth to points**, and points are the addresses
apparatus, supervised lines, protections, screens and logic all refer
to. Start by drawing a screen and there is nothing to bind symbols to.

Steps 1–4 can be done for you by the [Device
Wizard](help://wizard) (File → Device Wizard). The rest is ordinary
work in the tree.

---

## Step 1. A new project and its information

Top toolbar → **New**, then [Project
Information](help://info): the name (this is what the controller reports
as its project), the author, the description.

The root of the tree carries the same name — double-click renames it in
place.

## Step 2. Device composition

[Device Composition](help://devices) — tick the modules this controller
actually **has**. A module outside the composition does not exist: its
branch is not shown, and on the controller no object, no thread and no
tags are created for it.

Do this before configuring anything, so you do not fill in departments
that will not be there.

## Step 3. Locations

[Locations](help://locations) — short codes for places (a cabinet, the
boiler room, the gate). A card sits in one location and every point on
it inherits that location by default. Without this you cannot later
answer "where is this terminal".

## Step 4. I/O cards and the bus

[I/O Cards](help://io_cards) — one row per physical module: the id (the
first segment of every address), the model, which channel kinds it has
and how many of each, its Modbus address, its location.

**This is the moment points come into existence.** A card `ELA1` with 32
DI channels creates `ELA1.DI.1` … `ELA1.DI.32` in the point registry,
automatically.

The bus itself is configured here too (RTU or TCP, port, baud rate,
parity).

## Step 5. Describing the points

[Point Registry](help://points) — for each channel, write **what is
wired to it**, a technical note and, if it differs from the card's, its
own location. For analog points: signal type, the conversion from the
raw value to an engineering value, the unit and the decimals.

This description travels to the controller and is what the operator at
the cabinet reads. An address with no description is a channel number
and nothing more.

## Step 6. Apparatus

[Apparatus Registry](help://apparatus) — a breaker, a contactor, a
valve: its behavior, its feedback points and command points, the command
style (MAINTAINED / PULSE / PULSE_TOGGLE).

The apparatus is what the operator presses on the screen and what the
logic sees as one thing rather than as two raw outputs.

## Step 7. The synoptic diagram

[Synoptic Diagram](help://screens) — draw the installation and bind the
symbols to apparatus and points. The screen is stored **in the project**,
so the controller draws exactly what you drew, with no separate file.

Measurement visualisation lives here too — gauges, tanks and numeric
readouts bound to real points.

## Step 8. Logic

[Logic](help://logic) — a block diagram on those same addresses. Inputs,
gates, flip-flops, timers, analog blocks, the system signals `SYS.*` and
the alarm's `SSWIN.*`, outputs.

This is where you close everything the controller does not do by itself
— for instance routing `SSWIN.SIREN_ACTIVE` to the output a siren
physically hangs on.

## Step 9. The intrusion alarm (if it is in the composition)

In order: [Zones](help://zones) → [Supervised
Lines](help://lines) → [Users](help://intrusion_users). A line needs a
zone, and a user needs zones they are allowed to operate.

Power supervision and the sounder settings are on the Zones panel too.

## Step 10. Protection (if it is in the composition)

[Electrical Protection](help://protection_electrical) — ANSI function
settings, executed by the ADA01 card.
[Process Protection](help://protection_process) — upper and lower
thresholds on analog points, evaluated on the controller.

## Step 11. Check and save

[Check Project](help://validation) finds the mismatches tables do not
show: an apparatus pointing at a point that no longer exists, a point
owned by two apparatus at once, a line with no point, a module with data
but outside the composition.

Then **Save**. Only a saved file can be sent — the controller receives
the file on disk, not the contents of the window.

## Step 12. Send it to the controller

[Controller Connection](help://controller) — the address, an Engineer
token, **Send to Device**. Studio first compares revisions and settings:
if somebody changed something on the panel, you see a table of the
differences before anything is overwritten.

The controller **rebuilds itself from the new project without
restarting** — cards, points, apparatus, commands, the alarm system, the
logic and the panel. On the same page you can then check the [logic's
state](help://controller), the live settings and the counters.

---

## Worth doing as well

- [MQTT Integration](help://mqtt) — if the controller is to talk to Home
  Assistant.
- [Object Links](help://object_links) — if controllers are to see each
  other's values.
- [Protection Tests](help://protection_tests) — after commissioning, as
  proof that a protection tripped within a measured time.
""",
)

topic(
    "wizard", "start", "Kreator urządzenia", "Device Wizard",
    """
# Kreator urządzenia

**Plik → Kreator urządzenia.** Przeprowadza przez kroki 1–4
z [drogi projektu](help://workflow) w kolejności, w jakiej projekt ich
potrzebuje. Nic nie jest zapisywane, dopóki nie naciśniesz **Zakończ**.

## 1. Informacje o projekcie

Nazwa (wymagana — bez niej kreator nie idzie dalej), autor, opis.

## 2. Skład urządzenia

Zaznaczasz moduły, które ten sterownik ma. Moduły już obecne w projekcie
zostają zaznaczone; **usuwać moduł trzeba w dziale [Skład
urządzenia](help://devices)**, nie tutaj.

## 3. Lokalizacje

Kod (tylko litery A–Z i cyfry, np. `KOT` na kotłownię) plus opis.
Kreator od razu mówi, jeśli kod ma niedozwolony znak albo się powtarza.

## 4. Karty wejść/wyjść

Jeden wiersz na fizyczny moduł: id, model, zaznaczone rodzaje kanałów
z licznikami, adres Modbus, lokalizacja. Karta mająca DI **i** AI to
jeden wiersz z dwoma zaznaczeniami, nie dwa wiersze.

Sprawdzane od razu: puste id, kropka albo spacja w id, powtórzone id,
karta bez żadnego rodzaju kanału, powtórzony adres Modbus.

## 5. Podsumowanie i co dalej

Zestawienie: ile modułów, lokalizacji, kart i ile **punktów** powstanie.
Poniżej lista następnych kroków w drzewie — rejestr punktów, aparaty,
alarmówka/zabezpieczenia, ekrany, logika — i przypomnienie, że kreator
**nie zapisuje pliku**: zapis jest Twój, z górnego paska.
""",
    """
# Device Wizard

**File → Device Wizard.** It walks you through steps 1–4 of the
[project road](help://workflow), in the order the project needs them.
Nothing is written until you press **Finish**.

## 1. Project information

Name (required — the wizard will not continue without it), author,
description.

## 2. Device composition

Tick the modules this controller has. Modules already in the project
stay ticked; **removing a module is done in the [Device
Composition](help://devices) branch**, not here.

## 3. Locations

A code (letters A–Z and digits only, e.g. `KOT` for the boiler room)
plus a description. The wizard tells you straight away if a code has an
illegal character or repeats.

## 4. I/O cards

One row per physical module: id, model, the channel kinds ticked with
their counts, the Modbus address, the location. A card with both DI
**and** AI is one row with two ticks, not two rows.

Checked immediately: an empty id, a dot or a space in an id, a repeated
id, a card with no channel kind ticked, a repeated Modbus address.

## 5. Summary and next steps

A tally: how many modules, locations, cards and how many **points** will
be created. Below it the list of next steps in the tree — point
registry, apparatus, alarm/protection, screens, logic — and a reminder
that the wizard **does not save the file**: saving is yours, from the
top toolbar.
""",
)

topic(
    "window", "start", "Okno Studia", "The Studio window",
    """
# Okno Studia

## Lewa kolumna

Od góry: **LISTA URZĄDZEŃ** (obiekt i jego sterowniki — patrz
[Obiekt](help://site)), pod nią **drzewo projektu** aktywnego
sterownika.

Drzewo ma stałą strukturę, niezależnie od tego, co jest wypełnione:

- **PROJEKT** — Informacje, Skład urządzenia
- **KONFIGURACJA** — Lokalizacje, Karty, Rejestr punktów, Rejestr
  aparatów, Schemat synoptyczny, Logika, MQTT, Powiązania obiektu,
  Notatki serwisowe — w kolejności, w jakiej projekt ich potrzebuje:
  każdy dział po tych, na których się opiera
- **ALARMÓWKA** — Strefy, Linie dozorowe, Użytkownicy
- **ZABEZPIECZENIA** — Elektryczne, Procesowe
- **STEROWNIK** — Połączenie, Test zabezpieczeń
- **Pomoc**

Gałęzie modułów spoza [składu urządzenia](help://devices) są ukryte.

## Gdzie masz niezapisane zmiany

Dział, w którym coś edytowałeś, jest **czerwony z gwiazdką**
(`Lokalizacje *`) aż do zapisania projektu. Sterownik na liście urządzeń
oznacza się tak samo. To jedyne miejsce, w którym widać „co jeszcze nie
jest na dysku" bez otwierania każdego działu po kolei.

Korzeń drzewa nosi nazwę projektu — **dwuklik zmienia ją w miejscu**, to
samo pole co w [Informacjach o projekcie](help://info).

## Paski

**Górny pasek jest stały** i dotyczy zawsze **projektu**: Nowy, Otwórz,
Zapisz, Zapisz jako, Cofnij, Ponów, Pomoc. Działa na każdej gałęzi —
także tam, gdzie nie ma żadnego edytora.

**Pasek kontekstowy** pod nim należy do aktywnego działu. W Ekranach
i w Logice są tam własne narzędzia tych edytorów, razem z cyklem życia
ich własnych dokumentów.

## F1 — pomoc kontekstowa

W dowolnym momencie **F1** otwiera pomoc od razu na temacie działu,
w którym jesteś. Nie trzeba go szukać na liście.

## Język

**Ustawienia → Język** przełącza interfejs i tę pomoc. Klucze i wartości
zapisane w projekcie się nie zmieniają — zmienia się tylko to, co widzisz.
""",
    """
# The Studio window

## The left column

From the top: the **DEVICE LIST** (the object and its controllers — see
[Object](help://site)), and under it the **project tree** of the active
controller.

The tree has a fixed structure, regardless of what is filled in:

- **PROJECT** — Information, Device Composition
- **CONFIGURATION** — Locations, Cards, Point Registry, Apparatus
  Registry, Synoptic Diagram, Logic, MQTT, Object Links, Service Notes —
  in the order a project needs them: each branch after the ones it
  builds on
- **INTRUSION ALARM** — Zones, Supervised Lines, Users
- **PROTECTION** — Electrical, Process
- **CONTROLLER** — Connection, Protection Tests
- **Help**

Branches of modules outside the [device composition](help://devices) are
hidden.

## Where your unsaved edits are

A branch you edited is **red with an asterisk** (`Locations *`) until the
project is saved. A controller in the device list is marked the same
way. This is the one place that shows "what is not on disk yet" without
opening every branch in turn.

The root of the tree carries the project's name — **double-click renames
it in place**, the same field as in [Project
Information](help://info).

## Toolbars

**The top toolbar is fixed** and always acts on **the project**: New,
Open, Save, Save As, Undo, Redo, Help. It works on every branch —
including the ones with no editor at all.

**The contextual toolbar** below it belongs to the active department. In
Screens and Logic those are the editors' own tools, together with the
lifecycle of their own documents.

## F1 — contextual help

At any moment **F1** opens the help on the topic for the branch you are
in. No need to find it in the list.

## Language

**Settings → Language** switches the interface and this help. Keys and
values stored in the project do not change — only what you see does.
""",
)

topic(
    "site", "start", "Obiekt z kilku sterowników", "An object of several controllers",
    """
# Obiekt z kilku sterowników

Jeden `projekt.epw` opisuje **jeden** sterownik. Prawdziwa instalacja
bywa większa: dom ze sterownikiem w kotłowni i drugim przy bramie,
zakład z kilkoma szafami. Plik `obiekt.epwsite` spina je w jedną całość.

## Czym jest obiekt

Listą sterowników — nazwa i ścieżka do pliku projektu każdego z nich.
Same projekty zostają osobnymi plikami w swoich folderach; obiekt ich
nie wchłania.

## Menu Plik

| Pozycja | Co robi |
|---|---|
| **Nowy obiekt** | pusty obiekt, pytanie o nazwę |
| **Otwórz obiekt** | wczytuje `obiekt.epwsite` i jego sterowniki |
| **Dodaj sterownik do obiektu** | nowy, pusty projekt jako kolejne urządzenie |
| **Dodaj istniejący projekt** | dołącza `projekt.epw`, który już masz |
| **Zapisz obiekt** | zapisuje **wszystkie** sterowniki naraz |

„Zapisz" z górnego paska zapisuje tylko **aktywny** sterownik.

## Przełączanie

Kliknięcie sterownika na liście przełącza całe drzewo poniżej na jego
projekt. Edytory oddają swoje dokumenty przy przełączeniu — niezapisane
zmiany nie giną, sterownik zostaje czerwony z gwiazdką, dopóki go nie
zapiszesz.

## Usuwanie

**Usuń sterownik z obiektu** wyjmuje go z listy — **plik projektu
zostaje na dysku**. Jeśli ma niezapisane zmiany, Studio zapyta wprost,
czy je porzucić. Obiekt musi mieć co najmniej jeden sterownik.

## Po co to, poza porządkiem

Żeby sterowniki mogły widzieć nawzajem swoje wartości. To robią
[Powiązania obiektu](help://object_links) — punkt jednego sterownika
staje się tagiem `Link.*` u drugiego, przez MQTT.
""",
    """
# An object of several controllers

One `projekt.epw` describes **one** controller. A real installation is
often bigger: a house with a controller in the boiler room and another
at the gate, a plant with several cabinets. An `obiekt.epwsite` file
ties them into one whole.

## What an object is

A list of controllers — a name and a path to each one's project file.
The projects stay separate files in their own folders; the object does
not absorb them.

## The File menu

| Item | What it does |
|---|---|
| **New Object** | an empty object, asks for a name |
| **Open Object** | loads an `obiekt.epwsite` and its controllers |
| **Add Controller to Object** | a new, empty project as another device |
| **Add Existing Project** | attaches a `projekt.epw` you already have |
| **Save Object** | saves **all** the controllers at once |

"Save" on the top toolbar saves only the **active** controller.

## Switching

Clicking a controller in the list switches the whole tree below to its
project. The editors hand over their documents on the switch — unsaved
edits are not lost, and the controller stays red with an asterisk until
you save it.

## Removing

**Remove Controller from Object** takes it off the list — **the project
file stays on disk**. If it has unsaved edits, Studio asks outright
whether to discard them. An object needs at least one controller.

## Why, beyond tidiness

So controllers can see each other's values. That is what [Object
Links](help://object_links) do — one controller's point becomes a
`Link.*` tag on another, over MQTT.
""",
)

# =====================================================================
# PROJEKT
# =====================================================================

topic(
    "info", "project", "Informacje o projekcie", "Project Information",
    """
# Informacje o projekcie

Metryczka projektu i miejsce, z którego widać jego tożsamość.

| Pole | Do czego służy |
|---|---|
| **Plik** | ścieżka na dysku; „(niezapisany)", dopóki projekt nie ma pliku |
| **Nazwa** | to, czym projekt się przedstawia — sterownik podaje ją przez REST i pokazuje na panelu |
| **Autor** | kto go zaprojektował; zostaje w pliku |
| **Opis** | wolny tekst: co to za obiekt, co tu jest nietypowe |
| **Rewizja** | licznik zapisów — patrz [Zapis, rewizja i nastawy](help://save_versioning) |

**Nazwa jest też nazwą korzenia drzewa** — możesz ją zmienić dwuklikiem
tam albo tutaj, to jedno i to samo pole.

## Rewizji nie ustawia się ręcznie

Rośnie sama przy każdym zapisie i to po niej Studio i sterownik poznają,
że projekt się rozjechał. Przy wysyłce na sterownik jest porównywana —
patrz [Połączenie ze sterownikiem](help://controller).
""",
    """
# Project Information

The project's title page, and where its identity is visible.

| Field | What it is for |
|---|---|
| **File** | the path on disk; "(unsaved)" until the project has one |
| **Name** | what the project calls itself — the controller reports it over REST and shows it on the panel |
| **Author** | who designed it; it stays in the file |
| **Description** | free text: what this installation is, what is unusual about it |
| **Revision** | the save counter — see [Saving, revisions and settings](help://save_versioning) |

**The name is also the name of the tree's root** — change it by
double-clicking there or here, it is one and the same field.

## The revision is not set by hand

It grows on every save, and it is how Studio and the controller notice
that a project has diverged. It is compared when you send — see
[Controller Connection](help://controller).
""",
)

topic(
    "devices", "project", "Skład urządzenia", "Device Composition",
    """
# Skład urządzenia

Z jakich **modułów** składa się ten sterownik. Nie karty — funkcje.

Zaznaczenie decyduje o dwóch rzeczach naraz:

- **w Studiu** — czy gałąź tego modułu w ogóle pojawia się w drzewie;
- **w sterowniku** — czy moduł jest tworzony. Moduł spoza składu nie ma
  obiektu, nie ma wątku, nie ma tagów. Nie jest „wyłączony" — go nie ma.

## Kolumny

**Nazwa**, **Opis**, **Aktywny** (TAK/NIE — kliknięcie przełącza).

## Moduły

| Moduł | Co wnosi |
|---|---|
| Alarmówka | strefy, linie dozorowe, uzbrajanie |
| Zabezpieczenia elektryczne | nastawy ANSI realizowane przez ADA01 |
| Zabezpieczenia procesowe | progi na punktach analogowych |
| Trendy | historia wartości (Historian) |
| Jakość zasilania | parametry sieci: napięcie, THD, asymetria |
| Diagnostyka magistrali | liczniki ramek i błędów |
| Topologia systemu | widok faktycznego składu instalacji |
| Tryb inżynierski | dodatkowe narzędzia na poziomie Engineer |
| Wejścia analogowe | czy sterownik w ogóle obsługuje punkty AI |
| Liczniki łączeń | zliczanie załączeń i czasu pracy aparatów |
| Notatki serwisowe | dziennik serwisanta przy punktach |
| Historia alarmów | dziennik zdarzeń alarmówki |
| Podgląd alarmówki | żywy podgląd stref i linii na panelu |

## Wyłączenie nigdy nie kasuje danych

Jeśli moduł ma już dane w projekcie, Studio ostrzega wprost: gałąź
zniknie z drzewa, ale **dane zostają**. Ponowne włączenie przywraca je
w całości. Tak samo w sterowniku.

Moduł z danymi, ale poza składem, zgłasza [Sprawdź
projekt](help://validation) jako ostrzeżenie — nie błąd.
""",
    """
# Device Composition

Which **modules** this controller is made of. Not cards — functions.

A tick decides two things at once:

- **in Studio** — whether that module's branch appears in the tree at
  all;
- **on the controller** — whether the module is constructed. A module
  outside the composition has no object, no thread and no tags. It is
  not "disabled" — it is not there.

## Columns

**Name**, **Description**, **Active** (YES/NO — click to toggle).

## The modules

| Module | What it brings |
|---|---|
| Intrusion Alarm | zones, supervised lines, arming |
| Electrical Protection | ANSI settings executed by the ADA01 |
| Process Protection | thresholds on analog points |
| Trends | value history (the Historian) |
| Power Quality | mains parameters: voltage, THD, imbalance |
| Bus Diagnostics | frame and error counters |
| System Topology | a view of what the installation really consists of |
| Engineer Mode | extra verification tools at Engineer level |
| Analog Inputs | whether the controller handles AI points at all |
| Switching Counters | operation counts and running time for apparatus |
| Service Notes | the technician's logbook on points |
| Alarm History | the intrusion alarm's own event log |
| Alarm Live View | a live view of zones and lines on the panel |

## Disabling never deletes data

If a module already has data in the project, Studio says so outright:
the branch disappears from the tree, but **the data stays**. Re-enabling
brings it all back. The same on the controller.

A module with data but outside the composition is reported by [Check
Project](help://validation) as a warning — not an error.
""",
)

topic(
    "locations", "project", "Lokalizacje", "Locations",
    """
# Lokalizacje

Miejsca, do których odnoszą się karty i punkty: szafa, kotłownia, brama,
hala.

| Kolumna | Zasada |
|---|---|
| **Kod** | krótki, tylko **litery A–Z i cyfry**, unikalny (np. `KOT`, `BRAMA1`) |
| **Opis** | pełna nazwa, którą czyta człowiek |

## Dziedziczenie

Karta stoi w jednej lokalizacji. **Każdy jej punkt dziedziczy tę
lokalizację**, dopóki nie nadasz mu własnej w [Rejestrze
punktów](help://points) — rejestr pokazuje wtedy „(dziedziczona: …)".

Dzięki temu przeniesienie karty do innej szafy to jedna zmiana, a nie
trzydzieści dwie.

## Po co to jest naprawdę

Ta informacja jedzie na sterownik i ląduje przy tagu. Serwisant przy
szafie widzi nie tylko „ELA1.DI.7 — czujka hali", ale też gdzie ten
zacisk fizycznie jest. Bez lokalizacji zostaje pytanie, na które nikt
nie umie odpowiedzieć po dwóch latach.

Punkt wskazujący lokalizację, której nie ma na liście, zgłasza [Sprawdź
projekt](help://validation).
""",
    """
# Locations

The places cards and points refer to: a cabinet, the boiler room, the
gate, the hall.

| Column | Rule |
|---|---|
| **Code** | short, **letters A–Z and digits only**, unique (e.g. `KOT`, `GATE1`) |
| **Description** | the full name a human reads |

## Inheritance

A card sits in one location. **Every point on it inherits that
location** until you give it one of its own in the [Point
Registry](help://points) — the registry then shows "(inherited: …)".

This is why moving a card to another cabinet is one edit, not
thirty-two.

## What this is really for

The information travels to the controller and lands on the tag. A
technician at the cabinet sees not only "ELA1.DI.7 — hall detector" but
also where that terminal physically is. Without it you are left with a
question nobody can answer two years later.

A point naming a location that is not on the list is reported by [Check
Project](help://validation).
""",
)

topic(
    "io_cards", "project", "Karty wejść/wyjść", "I/O Cards",
    """
# Karty wejść/wyjść

Fizyczne moduły tego sterownika — i **jedyne** miejsce, w którym
powstają punkty.

## Wiersz = jeden moduł

| Kolumna | Znaczenie |
|---|---|
| **Id** | pierwszy człon każdego adresu tej karty (`ELA1` → `ELA1.DI.1`). Bez kropki i bez spacji |
| **Model** | katalogowy typ modułu |
| **Kanały (rodzaj i liczba)** | zaznaczasz rodzaje, które karta ma, i wpisujesz liczbę kanałów każdego |
| **Adres Modbus** | 1–247, unikalny w projekcie; puste = moduł nie jest jeszcze zaadresowany i **nie odpowiada na magistrali** |
| **Lokalizacja** | gdzie stoi; dziedziczą ją wszystkie jej punkty |
| **Odpowiada** | tylko w trybie „Na żywo": czy sterownik ma z niej odczyt |

Karta z **DI i AI** to **jeden wiersz z dwoma zaznaczeniami**, nie dwa
wiersze. Jeden fizyczny moduł ma jeden adres i jedną lokalizację, więc
dzielenie go na dwa wiersze zmuszałoby do wpisywania tego dwa razy.

## Rodzaje kanałów

`DI` wejścia dwustanowe, `DO` wyjścia dwustanowe, `AI` wejścia
analogowe, `AO` wyjścia analogowe. Adres ma postać `id.RODZAJ.numer`,
bez zer wiodących.

## Co się dzieje po dodaniu karty

Punkty powstają natychmiast w [Rejestrze punktów](help://points).
**Zmniejszenie liczby kanałów usuwa nadmiarowe punkty razem z ich
opisami** — z ostrzeżeniem. Usunięcie karty usuwa wszystkie jej punkty.

Na sterowniku dzieje się to samo przy [przeładowaniu
projektu](help://controller): karta skasowana w Studiu zabiera swoje
tagi.

## Magistrala Modbus

Pod tabelą: **Transport** (RTU po porcie szeregowym albo TCP), a do tego
port i prędkość oraz parzystość dla RTU, albo adres bramy i port TCP.

To jest ustawienie **projektu**. To, który sterownik fizycznie używa
Modbusa, a który symulatora, jest ustawieniem lokalnym sterownika —
widać je w [Połączeniu ze sterownikiem](help://controller).

## Lokalizacje

Przyciski **Dodaj lokalizację** / **Usuń lokalizację** prowadzą do tej
samej listy co dział [Lokalizacje](help://locations) — są tutaj, bo
lokalizacja jest polem karty i najczęściej brakuje jej właśnie w tym
momencie.
""",
    """
# I/O Cards

This controller's physical modules — and the **only** place where points
come into existence.

## One row = one module

| Column | Meaning |
|---|---|
| **Id** | the first segment of every address on this card (`ELA1` → `ELA1.DI.1`). No dot, no space |
| **Model** | the catalogue type of the module |
| **Channels (kind and count)** | tick the kinds the card has, and enter how many channels of each |
| **Modbus address** | 1–247, unique in the project; blank = the module is not addressed yet and **does not answer on the bus** |
| **Location** | where it sits; all of its points inherit it |
| **Responds** | in Live mode only: whether the controller is getting readings from it |

A card with **DI and AI** is **one row with two ticks**, not two rows.
One physical module has one address and one location, so splitting it
across two rows would mean entering those twice.

## Channel kinds

`DI` digital inputs, `DO` digital outputs, `AI` analog inputs, `AO`
analog outputs. An address is `id.KIND.number`, with no leading zeros.

## What happens when you add a card

The points appear immediately in the [Point Registry](help://points).
**Reducing the channel count deletes the surplus points together with
their descriptions** — with a warning. Removing a card removes all of
its points.

The same happens on the controller when the [project is
reloaded](help://controller): a card deleted in Studio takes its tags
with it.

## The Modbus bus

Below the table: **Transport** (RTU over a serial port, or TCP), then
the port, baud rate and parity for RTU, or the gateway address and TCP
port.

This is a **project** setting. Which controller physically uses Modbus
and which uses the simulator is a controller-local setting — visible in
[Controller Connection](help://controller).

## Locations

The **Add location** / **Remove location** buttons lead to the same list
as the [Locations](help://locations) branch — they are here because a
location is a field of a card, and this is usually the moment one turns
out to be missing.
""",
)

topic(
    "points", "project", "Rejestr punktów", "Point Registry",
    """
# Rejestr punktów

Wszystkie kanały wszystkich kart, w jednej tabeli. Punktów **nie dodaje
się tutaj** — rodzą się z [kart](help://io_cards). Tutaj im się nadaje
znaczenie.

Filtr **Karta** u góry zawęża widok do jednego modułu.

## Kolumny wspólne

| Kolumna | Co wpisać |
|---|---|
| **Adres** | `id.RODZAJ.numer` — tylko do odczytu, pochodzi z karty |
| **Opis** | co jest podłączone do tego zacisku; to czyta operator |
| **Lokalizacja** | pusta = dziedziczona z karty; można nadpisać |
| **Notatka techniczna** | dla serwisanta: numer żyły, listwa, typ czujki |
| **Aparat** | tylko do odczytu: który aparat zajął ten punkt |

**Ustaw lokalizację dla zaznaczonych…** nadaje lokalizację wielu punktom
naraz.

## Kolumny punktów analogowych (AI/AO)

| Kolumna | Znaczenie |
|---|---|
| **Typ sygnału** | `4-20mA`, `0-10V`, `0-3.3V ADC (raw)` albo „wartość gotowa" (bez przeliczania) |
| **Surowe min / max** | zakres wartości z karty |
| **Inż. min / max** | na co się to przelicza |
| **Jednostka** | `°C`, `bar`, `A`, `%` |
| **Miejsca dz.** | ile cyfr po przecinku pokazywać |

Przeliczenie jest liniowe. „Wartość gotowa" znaczy, że karta podaje już
wielkość inżynierską i nic nie trzeba skalować.

## Kolumna punktów DI

**Ostrzeżenie licznika przy** — po ilu łączeniach aparat na tym punkcie
ma się zgłosić do przeglądu. Liczy je moduł Liczników łączeń; stan
liczników podejrzysz w [Połączeniu ze
sterownikiem](help://controller).

## Tryb „Na żywo" i wymuszenia

Gdy Studio jest połączone ze sterownikiem, kolumna **Na żywo** pokazuje
bieżącą wartość każdego punktu. To samo działa w Kartach („Odpowiada")
i w edytorze ekranów.

**Tryb wymuszania (Engineer)** włącza operowanie wartością:

- **Wymuś wartość…** — przypina wybrany punkt do podanej wartości;
- **Zdejmij wymuszenie** / **Zdejmij wszystkie wymuszenia**;
- wymuszony punkt pokazuje `F → wartość` i kto go wymusił.

Wymuszenie jest narzędziem serwisanta: wymaga tokenu Engineer, jest
zapisywane w dzienniku sterownika, **utrzymuje się tylko dopóki Studio
potwierdza obecność** (heartbeat) i jest zdejmowane przy zamknięciu
połączenia, przy restarcie sterownika i przy [przeładowaniu
projektu](help://controller) — wymuszenie przypina tag, którego nowy
projekt może w ogóle nie mieć.
""",
    """
# Point Registry

Every channel of every card, in one table. Points are **not added
here** — they are born from [cards](help://io_cards). Here you give them
meaning.

The **Card** filter at the top narrows the view to one module.

## Columns for every point

| Column | What to enter |
|---|---|
| **Address** | `id.KIND.number` — read-only, it comes from the card |
| **Description** | what is wired to this terminal; this is what the operator reads |
| **Location** | blank = inherited from the card; you may override it |
| **Technical note** | for the technician: the core number, the terminal strip, the sensor type |
| **Device** | read-only: which apparatus has taken this point |

**Set Location for Selected…** gives a location to many points at once.

## Columns for analog points (AI/AO)

| Column | Meaning |
|---|---|
| **Signal type** | `4-20mA`, `0-10V`, `0-3.3V ADC (raw)` or "value ready" (no conversion) |
| **Raw min / max** | the range the card delivers |
| **Eng min / max** | what it converts to |
| **Unit** | `°C`, `bar`, `A`, `%` |
| **Decimals** | how many digits to show |

The conversion is linear. "Value ready" means the card already delivers
an engineering value and nothing needs scaling.

## The column for DI points

**Counter warning at** — after how many operations the apparatus on this
point should ask for a service. The Switching Counters module counts
them; the counters themselves can be read in [Controller
Connection](help://controller).

## Live mode and forcing

When Studio is connected to a controller, the **Live** column shows each
point's current value. The same works in Cards ("Responds") and in the
screen editor.

**Force mode (Engineer)** turns on operating on the value:

- **Force Value…** — pins the selected point to a value you give;
- **Release Force** / **Release All Forces**;
- a forced point shows `F → value` and who forced it.

A force is a technician's tool: it needs an Engineer token, it is
written to the controller's audit log, it **only lives as long as Studio
keeps confirming it is there** (a heartbeat), and it is released when
the connection closes, when the controller restarts, and when the
[project is reloaded](help://controller) — a force pins a tag the new
project may not even have.
""",
)

topic(
    "apparatus", "project", "Rejestr aparatów", "Apparatus Registry",
    """
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
""",
    """
# Apparatus Registry

An apparatus is a thing the operator handles as a whole: a breaker, a
contactor, a valve, a drive. The registry ties it to raw points.

| Column | Meaning |
|---|---|
| **Id** | its designation, unique (e.g. `Q1`, `KM1`) |
| **Behavior** | `SWITCHED`, `SIGNAL`, `MEASURED`, `MODULATED`, `SELECTOR` |
| **Kind** | the catalogue type — breaker, contactor, valve… |
| **Feedback** | the points you read the state from; the button opens the list |
| **Command** | the output points; assigned the same way |
| **Command style** | what the pulse looks like — see below |
| **Pulse** | pulse length in ms (for the pulsing styles) |

## Command styles

**MAINTAINED (level)** — energized = ON (one coil), or one coil per
direction held energized.

**PULSE (a pulse per direction)** — separate coils, a pulse for each
direction. An "on" state exists only when there is a single output.

**PULSE_TOGGLE (single-coil impulse relay)** — **one** R15/3P-class coil
behind one or two outputs. Every pulse **toggles**, so the runtime
pulses only when the feedback says the apparatus is not already in the
requested state. **Feedback is mandatory here** — without knowing the
current state every pulse would be a guess.

## What [Check Project](help://validation) looks for

- an apparatus pointing at a point that is not in the registry;
- an apparatus pointing at a point on a card no longer in the
  composition;
- **a point assigned to two apparatus at once**;
- a pulsing style with a pulse time of 0;
- `PULSE_TOGGLE` with no feedback, or with more than two outputs.

## Where the apparatus turns up later

- on the [screen](help://screens) — a symbol bound by `deviceId`;
- in the [logic](help://logic) — as one command, not two outputs;
- in [Protection Tests](help://protection_tests) — as a subject whose
  feedback time can be measured.
""",
)

topic(
    "screens", "project", "Schemat synoptyczny", "Synoptic Diagram",
    """
# Schemat synoptyczny

Edytor ekranów (Synoptic Editor) jako dział Studia. Rysujesz to, co
operator zobaczy na sterowniku — i wiążesz rysunek z prawdziwymi
punktami i aparatami. Pełny opis edytora — rozdziały o rysowaniu,
symbolach, przewodach, elementach ekranu i słownik — jest w tej samej
pomocy, w dziale [Ekrany — edytor synoptyki](help://synoptic/intro-what);
F1 na zaznaczonym symbolu otwiera jego temat.

## Co tu powstaje

- **Symbole aparatów** związane przez `deviceId` z [rejestrem
  aparatów](help://apparatus). Symbol pokazuje stan z potwierdzenia
  i przyjmuje kliknięcie jako komendę.
- **Przewody i sieci** — kolor idzie za stanem: sieć zasilona z punktu
  granicznego albo z zacisku aparatu, którego potwierdzenie mówi
  „załączony".
- **Pomiary** — wskaźniki, zbiorniki, wartości liczbowe związane
  z punktami analogowymi, z jednostką i liczbą miejsc po przecinku
  z [rejestru punktów](help://points).
- **Ściany, pokoje, otwory** — rzut obiektu; sterownik rysuje je tak
  samo, z wytłoczeniem pseudo-3D.

## Co panel pokaże

Nie cały niebieski canvas (domyślnie 24 × 13,5 m — jeden magazyn 6 × 4 m
byłby na nim plamką), tylko to, co narysowane, wpasowane w okno panelu
z niewielkim marginesem. Gdy chcesz sam zdecydować o kadrze: ustaw
powiększenie i przesunięcie tak, jak plan ma wyglądać przy szafce,
i wybierz **Widok → Ramka ekranu runtime → Ustaw z tego, co teraz
widzę**. Na planie pojawia się pomarańczowa przerywana ramka z podpisem
PANEL — dokładnie tyle pokaże sterownik. Ramka jest osobna dla każdego
ekranu; **Usuń ramkę** wraca do dopasowania automatycznego.

W inspektorze pomieszczenia X i Y to lewy górny róg pokoju liczony od
lewego górnego rogu planu, a szerokość i długość to jego rozmiar
w rzucie — wszystko w metrach.

## Widok główny i podgląd jak na panelu

W **Widok → Widoczne ekrany** gwiazdka przy ekranie oznacza **widok
główny** — ekran, od którego panel zaczyna. Bez gwiazdki panel zaczyna
od ekranu, który był otwarty przy zapisie.

**F11** (albo przycisk „Podgląd jak na panelu" na pasku ekranów, albo
Widok → Podgląd panelu) pokazuje widok główny na całym ekranie dokładnie
tak, jak pokaże go panel: bez siatki, bez uchwytów, wpasowany według
ramki ekranu runtime albo do treści. Kliknięcie aparatu **steruje** nim:
przy włączonym „Na żywo" komenda idzie do sterownika tą samą drogą co
z panelu (blokady i zabezpieczenia działają, odmowa pojawia się na pasku
stanu), a symbol podąża za potwierdzeniem ze sterownika; bez łączności
działa symulacja edytora. Pasek w rogu pozwala przełączyć ekran; **Esc**
albo F11 wraca do edycji.

## Ekran jest w projekcie

Nie ma osobnego pliku do wgrania. Ekran jedzie w `projekt.epw` i to
właśnie on jest **Widokiem Głównym** sterownika. Gdy projekt niesie
kilka ekranów, panel dostaje selektor.

Własny cykl życia dokumentu edytora (otwórz/zapisz `.epwsyn`) jest na
**pasku kontekstowym** tego działu, nie na górnym pasku — górny zawsze
dotyczy projektu.

## Punkty i karty widać od razu

Edytor korzysta z tego samego rejestru punktów co reszta Studia. Jeśli
listy adresów są puste, to znaczy, że nie ma jeszcze [kart](help://io_cards)
— ostrzeżenie stoi przy samym polu, razem z przyciskiem „+ Karta".

## Tryb „Na żywo"

Po połączeniu ze sterownikiem symbole w edytorze pokazują prawdziwy stan
— to samo przełączenie co w [rejestrze punktów](help://points).
""",
    """
# Synoptic Diagram

The screen editor (Synoptic Editor) as a Studio department. You draw
what the operator will see on the controller — and bind the drawing to
real points and apparatus. The editor's full description — chapters on
drawing, symbols, wires, screen elements and the glossary — is in this
same help, under [Screens — the synoptic editor](help://synoptic/intro-what);
F1 on a selected symbol opens its topic.

## What is made here

- **Apparatus symbols** bound by `deviceId` to the [apparatus
  registry](help://apparatus). A symbol shows the state from the
  feedback and takes a click as a command.
- **Wires and nets** — the colour follows the state: a net fed from a
  boundary point, or from the terminal of an apparatus whose feedback
  says "closed".
- **Measurements** — gauges, tanks and numeric readouts bound to analog
  points, with the unit and decimals from the [point
  registry](help://points).
- **Walls, rooms, openings** — the floor plan; the controller draws them
  the same way, with the same pseudo-3D extrusion.

## What the panel shows

Not the whole blue canvas (24 × 13.5 m by default — one 6 × 4 m
warehouse would be a stamp on it), but what is drawn, fitted into the
panel's window with a small margin. To decide the framing yourself: zoom
and pan until the plan looks as it should at the cabinet, then pick
**View → Runtime frame → Set from what I see now**. An orange dashed
frame labelled PANEL appears on the plan — exactly what the controller
will show. The frame is per screen; **Clear the frame** returns to the
automatic fit.

In the room inspector X and Y are the room's top-left corner measured
from the plan's top-left corner, and width and length are its size in
plan — all in metres.

## Main view and the preview as on the panel

In **View → Visible screens** the star next to a screen marks the **main
view** — the screen the panel opens with. Without a star the panel opens
with the screen that was active when the project was saved.

**F11** (or the "Preview as on the panel" button on the screens toolbar,
or View → Panel preview) shows the main view full screen exactly as the
panel shows it: no grid, no handles, fitted to the runtime frame or to
what is drawn. Clicking an apparatus **operates** it: with live on the
command goes to the controller down the same path as from the panel
(interlocks and safety checks apply, a refusal shows in the status bar)
and the symbol follows the controller's feedback; without a link the
editor's simulation answers. The bar in the corner switches the screen;
**Esc** or F11 returns to editing.

## The screen lives in the project

There is no separate file to upload. The screen travels inside
`projekt.epw` and it is the controller's **Main View**. When a project
carries several screens, the panel gets a selector.

The editor document's own lifecycle (open/save `.epwsyn`) is on **this
department's contextual toolbar**, not on the top one — the top toolbar
always acts on the project.

## Points and cards are visible immediately

The editor uses the same point registry as the rest of Studio. If the
address lists are empty it means there are no [cards](help://io_cards)
yet — the warning stands next to the field itself, with a "+ Card"
button.

## Live mode

Once connected to a controller the symbols in the editor show the real
state — the same switch as in the [point registry](help://points).
""",
)

topic(
    "logic", "project", "Logika", "Logic",
    """
# Logika

Pełny opis edytora logiki — pojęcia (etykiety, znaczniki, cykl skanu),
poradniki, katalog każdego bloku i skróty — jest w tej samej pomocy,
w dziale [Logika — edytor logiki](help://logic/welcome); F1 na
zaznaczonym bloku otwiera jego stronę z katalogu.

Edytor logiki sterowania (Logic Studio) jako dział Studia — biblioteka
bloków, symulacja, kompilacja i eksport do sterownika, te same narzędzia
co w samodzielnym Logic Studio, w jednej skórze z resztą działów.

## Na czym się programuje

Na **adresach z tego projektu**: `ELA1.DI.1`, `ADA1.DO.3`, punkty
analogowe z ich zakresem inżynierskim i jednostką. Karty i punkty są
mostkowane do edytora automatycznie — nie przepisujesz ich drugi raz.

Poza nimi masz:

- **bity wewnętrzne** (`M.`) i **bity retencyjne** (`MR.` / `MWR.`),
  które przeżywają restart sterownika;
- **sygnały systemowe `SYS.*`** — stan sterownika, poziom dostępu,
  komunikacja, generatory impulsów i migania;
- **sygnały alarmówki `SSWIN.*`** — uzbrojenie, alarm, pamięć alarmu,
  sabotaż, gotowość, a także sygnalizator i komendy.

## Sygnalizator: to Ty go podpinasz

Sterownik **nie steruje żadną syreną**. Wystawia stan — `SSWIN.SIREN_ACTIVE`
(ma dźwięczeć), `SIREN_TIME_LEFT`, `STROBE_ACTIVE` (lampa), `PANIC` —
a to, na którym wyjściu wisi syrena i przez jakie blokady, jest linią
schematu, którą rysujesz tutaj. Nastawy (jak długo wolno dźwięczeć, czy
linia napadowa ma być cicha) są w [Strefach](help://zones).

Tak samo `SSWIN.CMD_SILENCE` — wyciszenie samego dźwięku, bez ruszania
alarmu.

## Kompilacja i eksport

Logika jedzie na sterownik **skompilowana, w pliku projektu**. Zapis
projektu bierze aktualny wynik kompilacji; jeśli schemat się nie
kompiluje, Studio mówi to wprost i **zostawia poprzednią skompilowaną
wersję** — sterownik nigdy nie dostaje półproduktu.

Po wysłaniu możesz sprawdzić, czy skan naprawdę chodzi: [Połączenie ze
sterownikiem](help://controller) pokazuje liczbę bloków, czas cyklu,
liczbę skanów i ile wyjść prowadzi logika.

## Własna pomoc edytora

Logic Studio ma **własny, pełny dział pomocy**: pojęcia (etykiety kontra
znaczniki, opóźnienie o jeden skan, jakość sygnału analogowego, makra),
przewodniki krok po kroku i **katalog bloków** generowany z żywej
biblioteki — każdy blok z pinami, właściwościami i wartościami
domyślnymi. Otwórz go z poziomu edytora; **F1 na zaznaczonym bloku**
wchodzi od razu w jego opis.
""",
    """
# Logic

The logic editor's full description — concepts (labels, markers, the
scan cycle), guides, a page for every block and the shortcuts — is in
this same help, under [Logic — the logic editor](help://logic/welcome);
F1 on a selected block opens its catalog page.

The control-logic editor (Logic Studio) as a Studio department — the
block library, simulation, compilation and export to the controller: the
same tools as the standalone Logic Studio, in one skin with every other
department.

## What you program on

On **this project's addresses**: `ELA1.DI.1`, `ADA1.DO.3`, analog points
with their engineering range and unit. Cards and points are bridged into
the editor automatically — you do not enter them a second time.

Besides those you have:

- **internal bits** (`M.`) and **retentive bits** (`MR.` / `MWR.`) that
  survive a controller restart;
- **system signals `SYS.*`** — controller state, access level,
  communications, pulse and blink generators;
- **alarm signals `SSWIN.*`** — armed, alarm, alarm memory, tamper,
  readiness, and the sounder and its commands.

## The sounder: you are the one who wires it

The controller **drives no siren**. It publishes state —
`SSWIN.SIREN_ACTIVE` (it should be sounding), `SIREN_TIME_LEFT`,
`STROBE_ACTIVE` (the light), `PANIC` — and which output a siren hangs
on, through which interlocks, is a line of the diagram you draw here.
The settings (how long it may sound, whether a hold-up line stays
silent) are in [Zones](help://zones).

Likewise `SSWIN.CMD_SILENCE` — stopping the noise without touching the
alarm.

## Compiling and exporting

The logic travels to the controller **compiled, inside the project
file**. Saving the project takes the current compilation result; if the
diagram does not compile, Studio says so outright and **keeps the
previously compiled version** — the controller never receives a
half-finished program.

After sending you can check that the scan really runs: [Controller
Connection](help://controller) shows the block count, the cycle time,
the number of scans and how many outputs the logic drives.

## The editor's own help

Logic Studio has **its own, full help section**: concepts (labels versus
markers, the one-scan delay, analog signal quality, macros), step-by-step
guides, and a **block catalogue** generated from the live library —
every block with its pins, properties and defaults. Open it from inside
the editor; **F1 on a selected block** goes straight to its description.
""",
)

# =====================================================================
# ALARMÓWKA
# =====================================================================

topic(
    "zones", "alarm", "Strefy", "Zones",
    """
# Strefy

Strefa to kawałek obiektu uzbrajany i rozbrajany jako całość: parter,
hala, garaż. Każda [linia dozorowa](help://lines) należy do jednej
strefy.

| Kolumna | Znaczenie |
|---|---|
| **Id** | unikalne, np. `Z1` — pod tym identyfikatorem strefa występuje w tagach i w logice |
| **Nazwa** | czytelna, ta widnieje na panelu |
| **Czas na wyjście (s)** | ile masz na opuszczenie strefy po uzbrojeniu |
| **Czas na wejście (s)** | ile masz na rozbrojenie po naruszeniu linii zwłocznej |

Strefy, do której są przypisane linie, **nie da się usunąć** — najpierw
przepnij albo usuń jej linie.

## Nadzór zasilania

Dwa niezależne, opcjonalne sprawdzenia: **Sieć (230 V)** i **Akumulator**,
każde wskazujące punkt i to, czy stan „w porządku" jest wysoki.

Konwencja platformy: **sprawny sygnał czyta się jako wysoki**, żeby
przerwany przewód albo martwy moduł spadał w dół i wyglądał jak awaria,
a nie jak stan normalny. Nieskonfigurowane sprawdzenie zawsze czyta się
jako sprawne — „brak konfiguracji = brak nadzoru", bez błędów.

## Sygnalizator

Tu są **nastawy**, nie wyjście. Sterownik nie steruje żadną syreną —
wystawia stan (`SSWIN.SIREN_ACTIVE`, `SIREN_TIME_LEFT`,
`STROBE_ACTIVE`, `PANIC`), a wyjście podpinasz w [Logice](help://logic),
przez takie blokady, jakich wymaga instalacja.

| Nastawa | Znaczenie |
|---|---|
| **Sygnalizuj najdłużej** | po tym czasie `SIREN_ACTIVE` gaśnie samo, choć alarm trwa dalej; `0` = bez ograniczenia |
| **Linia napadowa nie uruchamia syreny** | domyślnie zaznaczone — patrz typ [Napadowa](help://lines) |

Lampa (`STROBE_ACTIVE`) przeżywa dźwięk: świeci od alarmu aż do
skasowania pamięci alarmu, żeby wracający na obiekt człowiek zobaczył,
że coś się wydarzyło.
""",
    """
# Zones

A zone is a part of the site armed and disarmed as one: the ground
floor, the hall, the garage. Every [supervised line](help://lines)
belongs to exactly one zone.

| Column | Meaning |
|---|---|
| **Id** | unique, e.g. `Z1` — the zone appears under this id in tags and in logic |
| **Name** | readable; this is what the panel shows |
| **Exit delay (s)** | how long you have to leave after arming |
| **Entry delay (s)** | how long you have to disarm after a delayed line is violated |

A zone that still has lines assigned **cannot be removed** — reassign or
remove its lines first.

## Power supervision

Two independent, optional checks: **Mains (230 V)** and **Battery**,
each naming a point and whether the "OK" state is high.

The platform's convention: **a healthy signal reads high**, so a severed
cable or a dead module fails low and looks like a fault rather than like
a normal state. An unconfigured check always reads healthy — "no
configuration means no supervision", with no errors.

## Sounder

These are **settings**, not an output. The controller drives no siren —
it publishes state (`SSWIN.SIREN_ACTIVE`, `SIREN_TIME_LEFT`,
`STROBE_ACTIVE`, `PANIC`), and you wire the output in
[Logic](help://logic), through whatever interlocks the installation
needs.

| Setting | Meaning |
|---|---|
| **Sound for at most** | after this, `SIREN_ACTIVE` goes false on its own although the alarm carries on; `0` = no limit |
| **A panic line does not sound the siren** | ticked by default — see the [Panic](help://lines) line type |

The light (`STROBE_ACTIVE`) outlives the noise: on from the alarm until
somebody clears the alarm memory, so a person coming back to the site
sees that something happened.
""",
)

topic(
    "lines", "alarm", "Linie dozorowe", "Supervised Lines",
    """
# Linie dozorowe

Jedna linia = jedna czujka (albo pętla czujek) na jednym punkcie
wejściowym. Tabela pokazuje id, nazwę, strefę, typ i skrót konfiguracji;
reszta jest w oknie **Konfiguruj…** — czternaście pól to nie jest wiersz
tabeli.

Bez [strefy](help://zones) nie da się dodać linii.

## Typy linii

| Typ | Kiedy alarmuje |
|---|---|
| **Natychmiastowa** | w chwili naruszenia, ale tylko przy UZBROJONEJ strefie |
| **Zwłoczna** | naruszenie przy uzbrojonej strefie uruchamia odliczanie wejścia; alarm dopiero, gdy nikt nie rozbroi |
| **Całodobowa** | natychmiast, **niezależnie od stanu strefy** — sabotaż, chroniona szafka |
| **Dozorowa** | **nigdy** nie alarmuje przy naruszeniu; sygnalizuje je logice (np. sterowanie oświetleniem). *Awaria* tej linii alarmuje jak w każdym innym typie |
| **Napadowa** | jak całodobowa — każdy stan strefy, także dozór nocny — ale **domyślnie cicha**: sens przycisku napadowego polega na tym, że stojący nad tobą człowiek się nie dowiaduje |

## Wejście

**Tryb stykowy** — zwykły styk: punkt plus stan normalny **NC**
(normalnie zwarty) albo **NO** (normalnie rozwarty). Linia czyta się
tylko jako spoczynek albo naruszenie.

**Tryb parametryzowany (EOL/2EOL)** — rezystor na końcu linii,
pojedynczy (EOL) albo podwójny (2EOL). Wtedy z jednej wartości
analogowej wychodzi pięć stanów, a nie dwa: **Spoczynek**, **Naruszenie**,
**Przerwa**, **Zwarcie**, **Sabotaż**. Okna wartości (min/max
w jednostkach inżynierskich) ustawiasz w tabeli poniżej — po jednym
wierszu na stan.

Właśnie dlatego 2EOL wykrywa przecięcie i zmostkowanie przewodu, czego
zwykły styk nie potrafi.

## Filtrowanie fałszywych alarmów

| Nastawa | Do czego |
|---|---|
| **Czas potwierdzenia (czułość)** | naruszenie krótsze niż to jest ignorowane |
| **Krotność naruszeń** | alarm dopiero po N naruszeniach |
| **Okno krotności** | w jakim czasie mają się zmieścić |
| **Blokada po liczbie alarmów** | linia „szalejąca" przestaje alarmować do rozbrojenia |
| **Czas podtrzymania alarmu** | jak długo strefa zostaje w ALARM po ustaniu przyczyny |

## Nadzór linii

**Czas ciszy przed podejrzeniem** — jeśli linia nie zgłosiła naruszenia
przez tak długo, dostaje status „podejrzana". To **ostrzeżenie, nie
alarm**: czujka, która nigdy nic nie widzi, bywa czujką martwą.

## Dozór nocny

**Czuwa nocą** — odznaczone znaczy, że ta linia przestaje dozorować, gdy
strefa jest uzbrojona w trybie nocnym. Zwykły wybór dla czujek ruchu
wewnątrz: ludzie chodzą po domu, a perymetr dalej czuwa. Linia
całodobowa i napadowa alarmują niezależnie od tego.
""",
    """
# Supervised Lines

One line = one detector (or loop of detectors) on one input point. The
table shows the id, name, zone, type and a summary of the configuration;
the rest is in the **Configure…** dialog — fourteen fields is not a
table row.

Without a [zone](help://zones) a line cannot be added.

## Line types

| Type | When it alarms |
|---|---|
| **Instant** | the moment it is violated, but only while the zone is ARMED |
| **Delayed** | a violation while armed starts the entry countdown; it alarms only if nobody disarms |
| **24-Hour** | immediately, **regardless of the zone's state** — tamper, a protected panel |
| **Supervisory** | **never** alarms on a violation; it signals it to the logic (lighting control, say). A *fault* on it alarms like on any other type |
| **Panic (hold-up)** | like 24-hour — any zone state, night arming included — but **silent by default**: the point is that the person standing over you does not learn you pressed it |

## The input

**Contact mode** — an ordinary contact: a point plus a normal state,
**NC** (normally closed) or **NO** (normally open). The line reads only
as secure or violated.

**Parametrized mode (EOL/2EOL)** — an end-of-line resistor, single (EOL)
or double (2EOL). One analog value then yields five states instead of
two: **Secure**, **Violated**, **Open fault**, **Short**, **Tamper**.
The value windows (min/max in engineering units) are set in the table
below — one row per state.

This is exactly why 2EOL detects a cut or a bridged cable, which a plain
contact cannot.

## False-alarm filtering

| Setting | What for |
|---|---|
| **Confirmation time (sensitivity)** | a violation shorter than this is ignored |
| **Violation count (multiplicity)** | it alarms only after N violations |
| **Multiplicity window** | the time they must fall within |
| **Lockout after alarm count** | a "chattering" line stops alarming until disarm |
| **Alarm hold time** | how long the zone stays in ALARM after the cause ends |

## Line supervision

**Silence time before suspect** — if the line has reported no violation
for this long, it is marked "suspect". This is a **warning, not an
alarm**: a detector that never sees anything may be a dead detector.

## Night arming

**Watches at night** — unticked means this line stops supervising while
its zone is armed in night mode. The usual choice for motion detectors
inside: people move about the house while the perimeter still watches.
24-hour and panic lines alarm regardless.
""",
)

topic(
    "intrusion_users", "alarm", "Użytkownicy alarmówki", "Alarm System Users",
    """
# Użytkownicy alarmówki

Kto wolno uzbrajać i rozbrajać które strefy — imiennie.

Trzy poziomy dostępu (User / Operator / Engineer) nie potrafiły
odpowiedzieć na pytanie „tylko Kowalski rozbroi magazyn": dwóch
operatorów to dla nich ten sam Operator. Ta kartoteka to potrafi.

| Kolumna | Znaczenie |
|---|---|
| **Id** | identyfikator osoby, np. `U1` — pod nim leżą jej sekrety na sterowniku |
| **Nazwisko** | co zobaczysz w dzienniku zamiast „Panel:Operator" |
| **Poziom** | jaki poziom dostępu daje jej własny kod |
| **Strefy** | które może obsługiwać; **pusta lista = wszystkie** |
| **Aktywny** | odznaczenie wyłącza konto, nie kasując go |

## Kodu tu nie ma i nigdy nie będzie

`projekt.epw` jedzie do Studia, do gita i po sieci. Kod na klawiaturę
i token zdalny to sekrety **egzemplarza sterownika** — leżą w jego
własnym pliku dostępu, pod id użytkownika, zapisane jednokierunkowo.

Z tego wynika porządek pracy: **osoba istnieje, gdy projekt wyląduje na
sterowniku, a loguje się, gdy ktoś nada jej kod na panelu**
(Ustawienia → Użytkownicy alarmówki, poziom Engineer). Tam też wydaje
się **token zdalny** dla [MQTT](help://mqtt) — pokazywany raz; token to
nie kod, więc wyciek z Home Assistanta nie otwiera panelu przy szafie.

## Co to zmienia w dzienniku

Dziennik pisze „Kowalski rozbroił strefę Hala", a nie „Panel:Operator".
Odmowa też: nie ta strefa, konto wyłączone, nieznany kod — wszystko
trafia do dziennika i do historii alarmowej.
""",
    """
# Alarm System Users

Who may arm and disarm which zones — by name.

The three access levels (User / Operator / Engineer) could never answer
"only Kowalski may disarm the warehouse": two operators are the same
Operator to them. This register can.

| Column | Meaning |
|---|---|
| **Id** | the person's identifier, e.g. `U1` — their secrets live under it on the controller |
| **Name** | what appears in the log instead of "Panel:Operator" |
| **Level** | the access level their own code grants |
| **Zones** | which ones they may operate; **an empty list = all of them** |
| **Active** | unticking disables the account without deleting it |

## The code is not here, and never will be

`projekt.epw` travels to Studio, into git and over the network. The
keypad code and the remote token are secrets of **one controller** —
they live in its own access file, under the user's id, stored one-way.

Hence the order of work: **a person exists the moment the project lands
on the controller, and can sign in the moment somebody sets their code
on the panel** (Settings → Alarm system users, Engineer level). That is
also where a **remote token** for [MQTT](help://mqtt) is issued — shown
once; a token is not a code, so a leak from Home Assistant does not open
the panel at the cabinet.

## What this changes in the log

The log says "Kowalski disarmed zone Hall", not "Panel:Operator".
Refusals too: not their zone, a disabled account, an unknown code — all
of it goes to the audit log and the alarm history.
""",
)

# =====================================================================
# ZABEZPIECZENIA
# =====================================================================

topic(
    "protection_electrical", "protection",
    "Zabezpieczenia elektryczne", "Electrical Protection",
    """
# Zabezpieczenia elektryczne

Nastawy funkcji przekaźnikowych ANSI. **Wykonuje je karta ADA01**, nie
program sterownika — tutaj ustala się wartości, z którymi ma pracować.

Po lewej drzewo: kategoria → funkcja → etap. Po prawej konfiguracja
zaznaczonego etapu.

## Kategorie i funkcje

| Kategoria | Funkcje |
|---|---|
| **Napięcie** | 27 podnapięciowe, 59 nadnapięciowe, 59N nadnapięciowe składowej zerowej, 47 kolejność / zanik faz |
| **Częstotliwość** | 81U podczęstotliwościowe, 81O nadczęstotliwościowe |
| **Prąd** | 50 nadprądowe bezzwłoczne, 51 nadprądowe zwłoczne, 46 składowa przeciwna, 49 przeciążenie cieplne, 50N/51N doziemne |
| **Zasilanie** | zanik napięcia sterowania, zanik zasilania technicznego |

Większość funkcji ma **dwa etapy** — zwykle pierwszy jako ostrzeżenie,
drugi jako wyłączenie.

## Pola etapu

| Pole | Znaczenie |
|---|---|
| **Włączony** | czy etap w ogóle pracuje |
| **Wielkość** | co jest mierzone (napięcie, prąd, częstotliwość…) — z katalogu |
| **Nastawa** | próg zadziałania, w jednostce funkcji |
| **Histereza** | o ile musi wrócić, żeby przestało być przekroczone |
| **Zwłoka** | po jakim czasie przekroczenia etap działa (ms) |
| **Akcja** | `Warning` (ostrzeżenie) albo `Trip` (wyłączenie) |

## Skąd biorą się wartości początkowe

Z katalogu ADA01. **Etap, którego projekt nie wymienia, ma wartość
domyślną z katalogu** — brak wpisu nie znaczy „wyłączone", znaczy
„domyślne". Po wysłaniu projektu warto porównać je z rzeczywistością
przez **Nastawy sterownika (na żywo)** w [Połączeniu ze
sterownikiem](help://controller).

Nastawy etapów są **nastawami**, nie strukturą: panel może je zmienić
(z wpisem do dziennika), a Studio zobaczy różnicę — patrz [Zapis,
rewizja i nastawy](help://save_versioning).
""",
    """
# Electrical Protection

The settings of ANSI relay functions. **The ADA01 card executes them**,
not the controller's program — here you set the values it works with.

On the left a tree: category → function → stage. On the right the
selected stage's configuration.

## Categories and functions

| Category | Functions |
|---|---|
| **Voltage** | 27 under voltage, 59 over voltage, 59N neutral overvoltage, 47 phase sequence / phase loss |
| **Frequency** | 81U under frequency, 81O over frequency |
| **Current** | 50 instantaneous overcurrent, 51 time overcurrent, 46 negative sequence, 49 thermal overload, 50N/51N earth fault |
| **Power supply** | control voltage loss, technical supply loss |

Most functions have **two stages** — usually the first as a warning, the
second as a trip.

## A stage's fields

| Field | Meaning |
|---|---|
| **Enabled** | whether the stage runs at all |
| **Quantity** | what is measured (voltage, current, frequency…) — from the catalogue |
| **Setting** | the pickup threshold, in the function's unit |
| **Hysteresis** | how far it must come back before it stops being exceeded |
| **Delay** | how long the excursion must last before the stage acts (ms) |
| **Action** | `Warning` or `Trip` |

## Where the initial values come from

From the ADA01 catalogue. **A stage the project does not mention has the
catalogue's default** — a missing entry does not mean "disabled", it
means "default". After sending the project it is worth comparing them
with reality through **Controller Settings (live)** in [Controller
Connection](help://controller).

Stage values are **settings**, not structure: the panel may change them
(with an audit entry) and Studio will see the difference — see [Saving,
revisions and settings](help://save_versioning).
""",
)

topic(
    "protection_process", "protection",
    "Zabezpieczenia procesowe", "Process Protection",
    """
# Zabezpieczenia procesowe

Progi na punktach analogowych, oceniane **w sterowniku**, na żywo.
Temperatura kotła, ciśnienie, poziom w zbiorniku.

Po lewej lista zabezpieczeń, po prawej konfiguracja zaznaczonego.

| Pole | Znaczenie |
|---|---|
| **Id / Nazwa** | identyfikator i czytelna nazwa |
| **Punkt** | punkt **analogowy (AI)** — inny rodzaj zgłosi [Sprawdź projekt](help://validation) |
| **Próg górny** | powyżej tego zabezpieczenie jest przekroczone |
| **Próg dolny** | poniżej tego również |
| **Histereza** | o ile wartość musi wrócić, żeby przestało być przekroczone |
| **Zwłoka (s)** | jak długo musi trwać przekroczenie, zanim zabezpieczenie zadziała |
| **En.** | czy zabezpieczenie jest włączone |

Progi są w **jednostkach inżynierskich** punktu — tych z [rejestru
punktów](help://points), nie w surowych wartościach z karty.

## Co się dzieje w sterowniku

Zabezpieczenie wystawia tag `Process.<id>.Exceeded`. Co ma się wtedy
stać — zamknięcie zaworu, zatrzymanie pompy, alarm — jest **linią
[logiki](help://logic)**, nie ustawieniem tutaj.

Histereza i zwłoka są po to, żeby drgająca wartość na granicy progu nie
przerzucała zabezpieczenia w kółko.

## Weryfikacja

**[Test zabezpieczeń](help://protection_tests)** potrafi to sprawdzić
bez rozbierania instalacji: wymusza wartość ponad próg, mierzy czas
zadziałania i porównuje go ze zwłoką, a potem wraca w zakres i mierzy
czas skasowania.
""",
    """
# Process Protection

Thresholds on analog points, evaluated **on the controller**, live.
Boiler temperature, pressure, a tank level.

On the left the list of protections, on the right the selected one's
configuration.

| Field | Meaning |
|---|---|
| **Id / Name** | identifier and a readable name |
| **Point** | an **analog (AI)** point — any other kind is reported by [Check Project](help://validation) |
| **Upper threshold** | above this the protection is exceeded |
| **Lower threshold** | below this it is exceeded too |
| **Hysteresis** | how far the value must come back before it stops being exceeded |
| **Delay (s)** | how long the excursion must last before the protection acts |
| **En.** | whether the protection is enabled |

Thresholds are in the point's **engineering units** — the ones from the
[point registry](help://points), not the card's raw values.

## What happens on the controller

The protection publishes a `Process.<id>.Exceeded` tag. What should then
happen — closing a valve, stopping a pump, raising an alarm — is a line
of [logic](help://logic), not a setting here.

Hysteresis and delay exist so that a value hovering on the threshold
does not flip the protection back and forth.

## Verification

**[Protection Tests](help://protection_tests)** can check this without
taking the installation apart: it forces the value past the threshold,
times the trip against the configured delay, then brings it back in band
and times the reset.
""",
)

# =====================================================================
# INTEGRACJA
# =====================================================================

topic(
    "mqtt", "integration", "Integracja MQTT", "MQTT Integration",
    """
# Integracja MQTT

Połączenie sterownika z brokerem MQTT (zwykle Home Assistant). To jest
**nastawa projektu**: jedzie z projektem na sterownik, panel może ją
zmienić (Engineer, z wpisem do dziennika), a różnice widać w
[Nastawach sterownika na żywo](help://controller).

## Broker

| Pole | Znaczenie |
|---|---|
| **Integracja MQTT włączona** | główny włącznik |
| **Adres brokera / Port** | gdzie się łączyć |
| **Użytkownik** | konto na brokerze |
| **TLS** | połączenie szyfrowane |
| **Client id** | identyfikator klienta na brokerze |
| **Prefiks tematów** | początek wszystkich tematów, domyślnie `epw/<id sterownika>` |
| **Interwał publikacji** | jak często wystawiać stan |
| **Domyślna strefa nieczułości** | o ile wartość musi się zmienić, żeby warto było ją publikować |
| **Limit kolejki** | ile wiadomości trzymać, gdy brokera nie ma |

**Hasła tu nie ma.** Wpisuje się je raz, na panelu sterownika
(Ustawienia → MQTT) i tam zostaje.

## Mapowania przychodzące (temat → tag `Link.*`)

Zdalny temat zasila lokalny tag `Link.<id>.In<n>` podanego typu.
Wartość starsza niż **„nieaktualna po"** jest oznaczana jako
nieaktualna, zamiast udawać świeżą.

Wiersze pochodzące z [Powiązań obiektu](help://object_links) są
oznaczone i **usuwa się je tam**, nie tutaj — Studio nigdy nie rusza
mapowań wpisanych ręcznie.

## Strefy nieczułości per tag

Osobna tabela dla punktów, które mają mieć inną czułość niż domyślna —
np. temperatura co 0,1°C, a ciśnienie co 0,01 bara.

## Sterowanie z Home Assistanta

Łącze nie jest już tylko podglądem: HAOS może uzbrajać i rozbrajać
alarmówkę, kasować alarm, wyciszać sygnalizator, zmieniać nastawy
zabezpieczeń i wydawać komendy aparatom. **Wymuszenia celowo zostają
poza tym kanałem** — to narzędzie kogoś stojącego przy szafie.

Tożsamość jedzie w wiadomości (token per osoba, wydawany na panelu —
patrz [Użytkownicy alarmówki](help://intrusion_users)), bo Home
Assistant ma jedno konto MQTT i broker nie odróżniłby dwóch osób.
Odrzucona komenda wygląda jak włam i podnosi **cichy alarm**.
""",
    """
# MQTT Integration

The controller's link to an MQTT broker (usually Home Assistant). This
is a **project setting**: it travels with the project to the controller,
the panel may change it (Engineer, audited), and differences show up in
[Controller Settings (live)](help://controller).

## Broker

| Field | Meaning |
|---|---|
| **MQTT integration enabled** | the master switch |
| **Broker address / Port** | where to connect |
| **Username** | the account on the broker |
| **TLS** | an encrypted connection |
| **Client id** | the client's identifier on the broker |
| **Topic prefix** | the start of every topic, by default `epw/<controller id>` |
| **Publish interval** | how often to publish state |
| **Default deadband** | how far a value must move before it is worth publishing |
| **Queue limit** | how many messages to hold while the broker is away |

**The password is not here.** It is entered once, on the controller's
panel (Settings → MQTT), and stays there.

## Incoming mappings (topic → `Link.*` tag)

A remote topic feeds a local `Link.<id>.In<n>` tag of the given type. A
value older than **"stale after"** is marked stale rather than pretending
to be fresh.

Rows that came from [Object Links](help://object_links) are marked and
**are removed there**, not here — Studio never touches mappings entered
by hand.

## Per-tag deadbands

A separate table for points that need a different sensitivity from the
default — temperature every 0.1 °C, pressure every 0.01 bar.

## Control from Home Assistant

The link is no longer a view-only one: HAOS can arm and disarm the alarm
system, clear an alarm, silence the sounder, change protection settings
and command apparatus. **Forces are deliberately outside this channel**
— a force is a tool for somebody standing at the cabinet.

Identity travels in the message (a token per person, issued on the panel
— see [Alarm System Users](help://intrusion_users)), because Home
Assistant has one MQTT account and the broker could not tell two people
apart. A refused command looks like a break-in and raises a **silent
alarm**.
""",
)

topic(
    "object_links", "integration", "Powiązania obiektu", "Object Links",
    """
# Powiązania obiektu

Punkt jednego sterownika, dostępny u drugiego. Przez MQTT: źródło
publikuje swoje tagi, cel je subskrybuje.

Potrzebny jest zapisany [obiekt z co najmniej dwoma
sterownikami](help://site).

| Kolumna | Znaczenie |
|---|---|
| **Źródło** | sterownik, który ma tę wartość |
| **Punkt źródłowy** | jego punkt |
| **Cel** | sterownik, który ma ją widzieć |
| **Tag `Link.*` na celu** | jak się będzie nazywać u celu: `Link.<Id>.In<nazwa>` |
| **Typ** | typ wartości |
| **Nieaktualna po** | po jakim czasie bez odświeżenia uznać ją za nieaktualną |

## Co Studio robi za Ciebie

Wpisuje mapowanie przychodzące do [MQTT](help://mqtt) sterownika
docelowego, a jeśli trzeba — włącza tam MQTT i nadaje prefiks tematów.
Usunięcie sterownika z obiektu zabiera jego powiązania.

Mapowań wpisanych ręcznie Studio **nigdy nie rusza**.

## Czym `Link.*` jest, a czym nie

Tag `Link.*` działa w [logice](help://logic) i na
[ekranach](help://screens) celu jak każdy inny tag — ale jest
**wyłącznie wartością do odczytu**. Nigdy nie jest komendą: nie da się
przez to sterować aparatem drugiego sterownika.

Nie ma też adresowania między projektami na ekranach — ekran celu wiąże
symbol z tagiem `Link.*` tak jak z każdym innym.
""",
    """
# Object Links

One controller's point, available on another. Over MQTT: the source
publishes its tags, the target subscribes to them.

You need a saved [object with at least two
controllers](help://site).

| Column | Meaning |
|---|---|
| **Source** | the controller that has the value |
| **Source point** | its point |
| **Target** | the controller that should see it |
| **`Link.*` tag on the target** | what it will be called there: `Link.<Id>.In<name>` |
| **Type** | the value's type |
| **Stale after** | how long without a refresh before it counts as stale |

## What Studio does for you

It writes the incoming mapping into the target controller's
[MQTT](help://mqtt) settings and, if needed, enables MQTT there and
gives it a topic prefix. Removing a controller from the object takes its
links with it.

Mappings entered by hand are **never** touched.

## What a `Link.*` tag is, and what it is not

A `Link.*` tag works in the target's [logic](help://logic) and
[screens](help://screens) like any other tag — but it is **a value to
read, only**. It is never a command: you cannot operate another
controller's apparatus through it.

There is no cross-project addressing on screens either — the target's
screen binds a symbol to a `Link.*` tag exactly as it would to any
other.
""",
)

# =====================================================================
# STEROWNIK
# =====================================================================

topic(
    "controller", "controller",
    "Połączenie ze sterownikiem", "Controller Connection",
    """
# Połączenie ze sterownikiem

Stąd projekt trafia na sterownik i stąd widać, co on naprawdę robi.

## Połączenie

**Adres (URL)** i **token dostępu** (Engineer — wydany na panelu
sterownika), potem **Testuj połączenie**. Stan pokazuje się obok:
nieznany / sprawdzanie / połączenie OK / błąd z powodem.

## Synchronizacja projektu

### Wyślij na urządzenie

1. **Projekt musi być zapisany** — sterownik dostaje plik z dysku, nie
   zawartość okna. Studio zaproponuje zapis.
2. Studio pobiera nagłówek sterownika i porównuje **rewizję**
   i **odcisk nastaw**.
3. Jeśli nastawy się rozjechały — tabela różnic: nastawa, wartość
   w Studiu, wartość na sterowniku. Możesz wysłać i nadpisać albo
   anulować.
4. Jeśli sterownik zmienił rewizję w międzyczasie, **nic nie jest
   wysyłane** i dostajesz o tym komunikat. Rozjazd = zatrzymać się.
5. Sterownik **przebudowuje się według nowego projektu bez restartu**:
   karty, punkty, aparaty, komendy, alarmówka, zabezpieczenia, logika
   i panel. Komunikat mówi wprost, czy tak się stało.

### Odbierz z urządzenia

Ściąga `projekt.epw` dokładnie w postaci, w jakiej sterownik z nim
pracuje — z nastawami zmienionymi na panelu i z notatkami serwisowymi,
które tam powstały.

## Podgląd na żywo

**Pobierz podgląd tagów** — tabela tag / wartość / jakość. Ten sam
kanał zasila tryb „Na żywo" w [rejestrze punktów](help://points),
w [kartach](help://io_cards) i w [edytorze ekranów](help://screens).

## Nastawy sterownika (na żywo)

**Pobierz nastawy**, opcjonalnie **odświeżaj co 5 s** i **tylko
różnice**. Tabela: nastawa / Studio / sterownik, z podświetleniem
rozbieżności.

**Przyjmij nastawy sterownika do projektu** przepisuje wartości ze
sterownika do projektu — to jest droga powrotna dla nastaw, które ktoś
poprawił przy szafie. Trzeba potem zapisać projekt.

## Ustawienia lokalne sterownika

**Pobierz ustawienia lokalne** — tylko do odczytu: język interfejsu,
REST, retencje historiana i dziennika, sterownik I/O, ścieżki plików.
To są ustawienia **egzemplarza**, nie instalacji, więc nie ma ich
w projekcie — ale nic na sterowniku nie jest niewidoczne ze Studia.

## Kopia zapasowa sterownika

**Pobierz kopię zapasową...** ściąga wszystko, co istnieje tylko na tym
sterowniku: liczniki łączeń, stan uzbrojenia, pamięć alarmu, bity
retencyjne logiki, dziennik audytowy, ustawienia lokalne i sam projekt.

Nie niesie **żadnych sekretów** — ani PIN-ów, ani kodów użytkowników
alarmówki, ani tokenów, ani hasła do brokera. Kopia to plik, który
opuszcza obiekt, a hasz czterocyfrowego PIN-u nie jest sekretem. Niesie
zamiast tego inwentarz: kto co MIAŁ, dzięki czemu odtworzenie kończy się
listą kontrolną z nazwiskami.

**Odtwórz z kopii zapasowej...** najpierw prosi sterownik o opisanie
kopii, pokazuje, co zostanie nadpisane, i dopiero wtedy ją wysyła.
Sterownik przebudowuje się według niej bez restartu. Własny adres REST
i sterownik wejść/wyjść zamiennika zostają nietknięte — opisują sprzęt,
na którym on pracuje, a nie ten, który padł.

Całą procedurę wymiany opisuje pomoc samego sterownika, rozdział „Kopia
zapasowa i wymiana".

## Liczniki łączeń

**Pobierz liczniki** — punkt, liczba załączeń, wyłączeń, czas w stanie
zamkniętym, próg ostrzegawczy (z [rejestru punktów](help://points)).

**Zeruj wybrany** / **Zeruj wszystkie** — nieodwracalne, wymagają tokenu
Engineer, trafiają do dziennika. Próg ostrzegawczy zostaje.

Sterownik bez modułu Liczników łączeń mówi to wprost, zamiast pokazywać
pustą tabelę.

## Stan logiki

Jedna linia, odświeżana razem z resztą:

- **RUNNING** — ile bloków, czas cyklu, liczba skanów, najdłuższy skan,
  ile wyjść prowadzi logika;
- **STOPPED** — program jest wczytany, ale skan nie chodzi: **blokady
  z tego programu nie są liczone**;
- **brak** — sterownik pracuje bez logiki użytkownika;
- **NOT running** — program został odrzucony, z powodem.
""",
    """
# Controller Connection

This is where the project reaches the controller, and where you see what
it is actually doing.

## Connection

The **Address (URL)** and an **access token** (Engineer — issued on the
controller's panel), then **Test Connection**. The state shows beside
it: unknown / testing / connection OK / failed, with the reason.

## Project sync

### Send to Device

1. **The project must be saved** — the controller receives the file on
   disk, not the contents of the window. Studio offers to save.
2. Studio fetches the controller's header and compares the **revision**
   and the **settings hash**.
3. If the settings have diverged — a table of differences: the setting,
   Studio's value, the controller's value. You can send and overwrite,
   or cancel.
4. If the controller's revision changed while you were deciding,
   **nothing is sent** and you are told. A divergence means stop.
5. The controller **rebuilds itself from the new project without
   restarting**: cards, points, apparatus, commands, the alarm system,
   protections, the logic and the panel. The message says outright
   whether that is what happened.

### Receive from Device

Pulls `projekt.epw` exactly as the controller is running it — with the
settings changed on the panel and the service notes written there.

## Live preview

**Fetch Tag Preview** — a tag / value / quality table. The same channel
feeds Live mode in the [point registry](help://points), in
[cards](help://io_cards) and in the [screen editor](help://screens).

## Controller settings (live)

**Fetch Settings**, optionally **refresh every 5 s** and **differences
only**. The table: setting / Studio / controller, with the differences
highlighted.

**Take controller values into project** writes the controller's values
into the project — the way back for settings somebody corrected at the
cabinet. Save the project afterwards to keep them.

## Controller-local settings

**Fetch Local Settings** — read-only: the interface language, REST, the
historian's and audit log's retention, the I/O driver, file paths. These
describe **this one controller**, not the installation, so they are not
in the project — but nothing on the controller is invisible from Studio.

## Controller backup

**Take a backup...** pulls everything that exists only on that
controller: the switching counters, the arming state, the alarm memory,
the retentive logic bits, the audit log, the local settings and the
project itself.

It carries **no secrets** — no PINs, no alarm users' codes, no tokens,
no broker password. A backup is a file that leaves the site, and a
four-digit PIN behind a hash is not a secret. What it carries instead is
an inventory of who HAD what, so a restore ends with a checklist naming
exactly what to set by hand.

**Restore from a backup...** asks the controller to describe the bundle
first, shows you what it is about to overwrite, and only then sends it.
The controller rebuilds itself from it without restarting. The
replacement's own REST address and I/O driver are left alone — they
describe the hardware it is running on, not the hardware that died.

The whole replacement procedure is on the controller's own help, under
"Backup and replacement".

## Switching counters

**Fetch Counters** — the point, closes, opens, closed time, the warning
threshold (from the [point registry](help://points)).

**Reset Selected** / **Reset All** — irreversible, they need an Engineer
token and they go into the audit log. The warning threshold stays.

A controller with no Switching Counters module says so, rather than
showing an empty table.

## Logic state

One line, refreshed with the rest:

- **RUNNING** — how many blocks, the cycle time, the scan count, the
  longest scan, how many outputs the logic drives;
- **STOPPED** — a program is loaded but the scan is not running: **the
  interlocks in it are not being evaluated**;
- **none** — the controller runs without user logic;
- **NOT running** — the program was refused, with the reason.
""",
)

topic(
    "protection_tests", "controller", "Test zabezpieczeń", "Protection Tests",
    """
# Test zabezpieczeń

Wewnętrzny Omicron: sterownik sam wymusza stan, mierzy czas reakcji
i zostawia raport. Bez walizki pomiarowej i bez rozbierania instalacji.

Wymaga tokenu Engineer; każdy test trafia do dziennika, a raporty
zostają **na sterowniku**.

## Co da się przetestować

**Zabezpieczenie procesowe** — punkt analogowy jest wymuszany ponad
próg, czas zadziałania mierzony względem skonfigurowanej zwłoki, potem
wartość wraca w zakres i mierzony jest czas skasowania.

**Aparat** — komenda idzie **tą samą drogą co z panelu**: blokady
logiki, safety kernel, tryb szkoleniowy i wymuszenia działają bez zmian.
Mierzony jest czas sprzężenia zwrotnego, potem stan jest przywracany.

Lista **Co można przetestować** pokazuje rodzaj, id, nazwę, nastawy
i stan: `gotowe`, `wyłączone`, `zadziałane — najpierw skasuj`.

## Czego ten test nie obejmuje

**Ścieżki zabezpieczeń elektrycznych (ADA01).** Funkcje ANSI wykonuje
karta, a nie program sterownika — tego nie da się sprawdzić wymuszeniem
tagu.

## Raporty

Tabela: start, rodzaj, obiekt, wynik, nastawy, **zmierzone**, powód.
Dwuklik otwiera kroki pojedynczego testu — co po kolei zrobił i co
zmierzył.

**Zapisz raporty jako CSV** eksportuje je do pliku, do dokumentacji
odbiorowej.

Starszy EPW-OS bez tej funkcji jest rozpoznawany i mówi to wprost.
""",
    """
# Protection Tests

The internal Omicron: the controller forces a state itself, measures the
response time and keeps a report. No test set, and no taking the
installation apart.

It needs an Engineer token; every test is audited, and the reports stay
**on the controller**.

## What can be tested

**A process protection** — its analog point is forced past the
threshold, the trip is timed against the configured delay, then the
value goes back in band and the reset is timed.

**An apparatus** — the command goes **down the same path as from the
panel**: logic interlocks, the safety kernel, training mode and forces
all apply unchanged. The feedback is timed, then the state is restored.

The **What can be tested** list shows the kind, id, name, settings and
state: `ready`, `disabled`, `tripped — clear it first`.

## What this test does not cover

**The electrical protection path (ADA01).** The card executes the ANSI
functions, not the controller's program — that cannot be checked by
forcing a tag.

## Reports

A table: started, kind, subject, result, settings, **measured**, reason.
Double-click opens one test's steps — what it did, in order, and what it
measured.

**Save Reports as CSV** exports them to a file, for the commissioning
documentation.

An older EPW-OS without this feature is recognised and says so.
""",
)

topic(
    "service_notes", "controller", "Notatki serwisowe", "Service Notes",
    """
# Notatki serwisowe

Dziennik serwisowy urządzeń, pisany **na panelu sterownika** (poziom
Operator lub wyższy). Tutaj jest **tylko do odczytu**.

| Kolumna | Znaczenie |
|---|---|
| **Urządzenie / punkt** | czego wpis dotyczy |
| **Opis** | opis tego urządzenia z projektu |
| **Data** | kiedy wpis powstał |
| **Poziom** | na jakim poziomie dostępu go napisano |
| **Wpis** | treść |

## Wpisów się nie edytuje ani nie kasuje

Ani na panelu, ani tutaj. Dziennik, który da się poprawić, przestaje być
dziennikiem.

## Jak trafiają do Studia

Przez **Odbierz z urządzenia** albo **Przyjmij nastawy sterownika do
projektu** w [Połączeniu ze sterownikiem](help://controller). Notatki są
częścią projektu, więc jadą razem z nim.
""",
    """
# Service Notes

The devices' service logbook, written **on the controller's panel**
(Operator level or higher). Here it is **read-only**.

| Column | Meaning |
|---|---|
| **Device / point** | what the entry is about |
| **Description** | that device's description from the project |
| **Date** | when the entry was made |
| **Level** | the access level it was written at |
| **Entry** | the text |

## Entries are never edited or deleted

Neither on the panel nor here. A logbook that can be corrected stops
being a logbook.

## How they reach Studio

Through **Receive from Device** or **Take controller values into
project** in [Controller Connection](help://controller). The notes are
part of the project, so they travel with it.
""",
)

# =====================================================================
# PRACA Z PROJEKTEM
# =====================================================================

topic(
    "validation", "working", "Sprawdź projekt", "Check Project",
    """
# Sprawdź projekt

Szuka rozjazdów, których nie widać w żadnej pojedynczej tabeli, bo
dotyczą **dwóch działów naraz**. Dwuklik na wpisie przenosi prosto do
miejsca problemu.

Podsumowanie rozdziela **Błędy** i **Ostrzeżenia**.

## Co sprawdza

| Wpis | Co to znaczy |
|---|---|
| aparat wskazuje punkt, którego nie ma w rejestrze | punkt został skasowany albo adres jest literówką |
| aparat wskazuje punkt na karcie, której już nie ma w składzie | karta zniknęła, przypisanie zostało |
| **punkt przypisany do więcej niż jednego aparatu** | dwa aparaty sterowałyby tym samym wyjściem |
| punkt wskazuje lokalizację spoza listy | lokalizacja została usunięta albo przemianowana |
| linia dozorowa wskazuje punkt, którego nie ma | linia nie ma czego pilnować |
| zabezpieczenie procesowe wskazuje punkt, którego nie ma | jak wyżej |
| zabezpieczenie procesowe wskazuje punkt **nie-AI** | progi wymagają wartości analogowej |
| moduł ma dane, ale jest poza składem | **ostrzeżenie**: gałąź ukryta, dane nietknięte |
| styl impulsowy z czasem impulsu 0 ms | impuls o zerowej długości nic nie zrobi |
| `PULSE_TOGGLE` bez potwierdzenia | każdy impuls przerzuca, więc stan musi być znany |
| `PULSE_TOGGLE` z więcej niż dwoma wyjściami | ten styl obsługuje jedno albo dwa |

## Kiedy to robić

Przed każdą wysyłką na sterownik. Sterownik przyjmie projekt, który nie
przeszedł tego sprawdzenia — format jest poprawny, więc nie ma podstaw,
żeby odmówić — ale aparat wskazujący nieistniejący punkt po prostu nie
zadziała, i dowiesz się o tym przy szafie, a nie przy biurku.
""",
    """
# Check Project

It looks for the mismatches no single table can show, because they span
**two departments at once**. Double-click an entry to jump straight to
the problem.

The summary separates **Errors** from **Warnings**.

## What it checks

| Entry | What it means |
|---|---|
| an apparatus points at a point that is not in the registry | the point was deleted, or the address is a typo |
| an apparatus points at a point on a card no longer in the composition | the card is gone, the assignment stayed |
| **a point assigned to more than one apparatus** | two apparatus would drive the same output |
| a point names a location that is not on the list | the location was removed or renamed |
| a supervised line points at a point that does not exist | the line has nothing to watch |
| a process protection points at a point that does not exist | as above |
| a process protection points at a **non-AI** point | thresholds need an analog value |
| a module has data but is outside the composition | **a warning**: the branch is hidden, the data untouched |
| a pulsing style with a 0 ms pulse | a zero-length pulse does nothing |
| `PULSE_TOGGLE` with no feedback | every pulse toggles, so the state must be known |
| `PULSE_TOGGLE` with more than two outputs | this style takes one or two |

## When to run it

Before every send. The controller will accept a project that has not
passed this check — the format is valid, so there are no grounds to
refuse it — but an apparatus pointing at a point that does not exist
simply will not work, and you will find that out at the cabinet rather
than at the desk.
""",
)

topic(
    "save_versioning", "working",
    "Zapis, rewizja i nastawy", "Saving, revisions and settings",
    """
# Zapis, rewizja i nastawy

## Trzy pliki sterownika

| Plik | Co w nim jest | Kto pisze |
|---|---|---|
| `projekt.epw` | projekt: karty, punkty, aparaty, skład, ekrany, logika, alarmówka, zabezpieczenia | Studio; sterownik tylko nastawy |
| `runtime_state.json` | stan: liczniki, uzbrojenie, wykluczenia, pamięć alarmu | wyłącznie sterownik |
| pliki lokalne sterownika | kody, tokeny, hasła, język, REST, retencje | wyłącznie sterownik |

Sekrety nie są w projekcie **nigdy** — projekt jedzie do Studia, do gita
i po sieci.

## Rewizja

Rośnie przy każdym zapisie i niesie informację, **kto zapisał**: Studio
albo panel. Dzięki temu przy wysyłce da się rozpoznać, że sterownik ma
nowszą wersję niż ta, z której wychodzisz — i **zatrzymać się** zamiast
nadpisać cudzą zmianę.

## Struktura kontra nastawa

To jest podział, który decyduje, co wolno zmienić przy szafie:

**Struktura** — co w ogóle istnieje: karty, punkty, aparaty, skład,
strefy, linie, ekrany, logika. Projektuje się to **wyłącznie w Studiu**.
Panel odmawia zmiany struktury i zapisuje tę odmowę w dzienniku.

**Nastawa** — wartość czegoś, co istnieje: czasy strefy, progi
zabezpieczeń, filtry linii, skalowanie punktu analogowego, MQTT,
sygnalizator. Panel może je zmienić (z wpisem do dziennika i rewizją
„panel"), a Studio widzi różnicę i może je przyjąć — patrz [Połączenie
ze sterownikiem](help://controller).

**Odcisk nastaw** (settings hash) to skrót wszystkich nastaw naraz.
Studio porównuje go przed wysłaniem, żeby nie pytać o różnice, których
nie ma.

## Co się zapisuje razem z projektem

Ekran z [edytora ekranów](help://screens) i **skompilowana**
[logika](help://logic). Jeśli logika się nie kompiluje, Studio mówi to
wprost i zostawia poprzednią skompilowaną wersję; jeśli edytor ekranów
odmówi wydania dokumentu, zapyta, czy zapisać projekt z **poprzednio**
zapisanymi ekranami.

## Kopia i wycofanie

Instalacja na sterowniku zostawia poprzedni plik jako `projekt.epw.bak`.
Jeśli nowy okaże się nie do wczytania przy starcie, poprzedni wraca sam,
a odrzucony zostaje do obejrzenia.
""",
    """
# Saving, revisions and settings

## The controller's three files

| File | What is in it | Who writes it |
|---|---|---|
| `projekt.epw` | the project: cards, points, apparatus, composition, screens, logic, alarm, protections | Studio; the controller only settings |
| `runtime_state.json` | state: counters, arming, bypasses, alarm memory | the controller only |
| the controller's local files | codes, tokens, passwords, language, REST, retentions | the controller only |

Secrets are **never** in the project — a project travels to Studio, into
git and over the network.

## The revision

It grows on every save and carries **who saved it**: Studio or the
panel. That is how a send can tell that the controller holds a newer
version than the one you started from — and **stop** instead of
overwriting somebody else's change.

## Structure versus setting

This is the split that decides what may be changed at the cabinet:

**Structure** — what exists at all: cards, points, apparatus, the
composition, zones, lines, screens, logic. Designed **in Studio only**.
The panel refuses a structural change and writes that refusal to the
audit log.

**A setting** — the value of something that exists: zone delays,
protection thresholds, line filters, an analog point's scaling, MQTT,
the sounder. The panel may change those (with an audit entry and a
"panel" revision), and Studio sees the difference and can take it — see
[Controller Connection](help://controller).

**The settings hash** is a digest of every setting at once. Studio
compares it before sending, so it does not ask about differences that
are not there.

## What is saved with the project

The screen from the [screen editor](help://screens) and the
**compiled** [logic](help://logic). If the logic does not compile,
Studio says so and keeps the previously compiled version; if the screen
editor refuses to hand over its document, it asks whether to save the
project with the **previously** saved screens.

## Backup and rollback

Installing on the controller keeps the previous file as
`projekt.epw.bak`. If the new one turns out to be unreadable at a later
start, the previous one comes back by itself and the refused one is kept
for inspection.
""",
)

topic(
    "glossary", "working", "Słownik pojęć", "Glossary",
    """
# Słownik pojęć

**Adres** — `id_karty.RODZAJ.numer`, np. `ELA1.DI.1`. Jedyny sposób
wskazania kanału w całej platformie.

**Aparat** — rzecz obsługiwana jako całość (wyłącznik, stycznik, zawór),
związana z punktami potwierdzenia i sterowania. Patrz
[Rejestr aparatów](help://apparatus).

**Bit retencyjny** (`MR.` / `MWR.`) — bit wewnętrzny logiki, który
przeżywa restart sterownika.

**Karta** — fizyczny moduł wejść/wyjść. Patrz [Karty](help://io_cards).

**Linia dozorowa** — jedna czujka alarmówki na jednym punkcie. Patrz
[Linie](help://lines).

**Lokalizacja** — kod miejsca, dziedziczony z karty na punkty. Patrz
[Lokalizacje](help://locations).

**Nastawa** — wartość, którą wolno zmienić na panelu. Przeciwieństwo
struktury. Patrz [Zapis i rewizja](help://save_versioning).

**Obiekt** (`obiekt.epwsite`) — kilka sterowników jako jedna instalacja.
Patrz [Obiekt](help://site).

**Odcisk nastaw** (settings hash) — skrót wszystkich nastaw, używany do
wykrycia rozjazdu ze sterownikiem.

**Punkt** — jeden kanał karty, z opisem, lokalizacją i (dla analogowych)
skalowaniem. Patrz [Rejestr punktów](help://points).

**Rewizja** — licznik zapisów projektu.

**Skład urządzenia** — z jakich modułów składa się sterownik. Patrz
[Skład](help://devices).

**Strefa** — kawałek obiektu uzbrajany jako całość. Patrz
[Strefy](help://zones).

**`SSWIN.*`** — sygnały alarmówki dostępne w logice: uzbrojenie, alarm,
pamięć, sabotaż, sygnalizator, komendy.

**`SYS.*`** — sygnały systemowe sterownika dostępne w logice.

**Tag** — nazwana wartość w sterowniku. Adres punktu jest tagiem;
`Security.*`, `Process.*`, `Link.*`, `System.*` też.

**Tryb „Na żywo"** — pokazywanie prawdziwych wartości ze sterownika
w tabelach i w edytorze ekranów.

**Wymuszenie** — przypięcie tagu do wartości przez serwisanta. Wymaga
Engineera, jest w dzienniku, nie przeżywa restartu ani przeładowania
projektu. Patrz [Rejestr punktów](help://points).
""",
    """
# Glossary

**Address** — `card_id.KIND.number`, e.g. `ELA1.DI.1`. The only way a
channel is named anywhere on the platform.

**Apparatus** — a thing handled as a whole (a breaker, a contactor, a
valve), tied to feedback and command points. See [Apparatus
Registry](help://apparatus).

**Card** — a physical I/O module. See [I/O Cards](help://io_cards).

**Device composition** — which modules a controller is made of. See
[Composition](help://devices).

**Force** — a technician pinning a tag to a value. Needs Engineer, is
audited, and survives neither a restart nor a project reload. See [Point
Registry](help://points).

**Live mode** — showing the controller's real values in the tables and
in the screen editor.

**Location** — a place code, inherited from a card by its points. See
[Locations](help://locations).

**Object** (`obiekt.epwsite`) — several controllers as one installation.
See [Object](help://site).

**Point** — one channel of a card, with its description, location and
(for analog ones) its scaling. See [Point Registry](help://points).

**Retentive bit** (`MR.` / `MWR.`) — a logic bit that survives a
controller restart.

**Revision** — the project's save counter.

**Setting** — a value the panel is allowed to change. The opposite of
structure. See [Saving and revisions](help://save_versioning).

**Settings hash** — a digest of every setting, used to detect a
divergence from the controller.

**`SSWIN.*`** — the alarm system's signals available in logic: armed,
alarm, memory, tamper, the sounder, the commands.

**Supervised line** — one alarm detector on one point. See
[Lines](help://lines).

**`SYS.*`** — the controller's system signals available in logic.

**Tag** — a named value in the controller. A point's address is a tag;
so are `Security.*`, `Process.*`, `Link.*` and `System.*`.

**Zone** — a part of the site armed as one. See [Zones](help://zones).
""",
)

# =====================================================================
# O PROGRAMIE
# =====================================================================

topic(
    "about", "about_chapter", "O programie EPW Studio", "About EPW Studio",
    """
# EPW Studio

**Wersja {version}**

Jedna aplikacja inżynierska do projektowania instalacji na platformie
EPW - schemat synoptyczny, logika sterowania, rejestr punktów, aparaty,
alarmówka, zabezpieczenia, połączenie ze sterownikiem.

## Skąd się wziął

Synoptic Editor i Logic Studio zaczynały jako dwa osobne programy,
uruchamiane osobno. Studio powstało, żeby to skończyć - jedno okno,
jedno drzewo projektu, jedna szata graficzna. Ekrany i Logika są dziś
działami Studio, nie osobnymi produktami.

## Czym się różni

Wiele narzędzi inżynierskich do automatyki wymaga osobnego programu do
każdego aspektu projektu - inny do rysowania ekranów, inny do logiki,
inny do konfiguracji alarmów. Studio trzyma to wszystko w jednym
miejscu, w jednym pliku projektu (`projekt.epw`), z jednym rejestrem
punktów, który widzi każdy dział naraz.

## Skąd ten wygląd

Ta sama estetyka lat dziewięćdziesiątych co EPW OS (runtime) - z tego
samego powodu: czytelność, nie sentyment sam w sobie, choć ten też ma
tu miejsce.

## Autor

mgr inż. Waldemar Bronisz, BroniszLabs - ten sam autor co EPW OS, ten
sam projekt, inna warstwa: tam sterownik, tutaj narzędzie, którym się
go projektuje.

## Licencja i dostępność

Tak jak EPW OS - darmowe, do korzystania i rozwijania.
""",
    """
# EPW Studio

**Version {version}**

A single engineering application for designing EPW platform
installations - synoptic diagram, control logic, point registry,
apparatus, intrusion alarm, protection settings, controller connection.

## Where it came from

Synoptic Editor and Logic Studio started as two separate programs, each
launched on its own. Studio was built to end that - one window, one
project tree, one skin. Screens and Logic are departments of Studio
today, not separate products.

## What makes it different

Many engineering tools for automation need a separate program for each
aspect of a project - one for drawing screens, another for the logic,
another for alarm configuration. Studio keeps all of it in one place,
in one project file (`projekt.epw`), with one point registry every
department can see at once.

## Where the look comes from

The same 1990s aesthetic as EPW OS (runtime) - for the same reason:
legibility, not nostalgia for its own sake, though that has a place
here too.

## Author

Waldemar Bronisz, MSc Eng., BroniszLabs - the same author as EPW OS,
the same project, a different layer: there the controller, here the
tool used to design it.

## License and availability

Same as EPW OS - free, to use and to build on.
""",
)

# =====================================================================
# WRITE
# =====================================================================

for lang in ("pl", "en"):
    lang_dir = os.path.join(OUT_DIR, lang)
    os.makedirs(lang_dir, exist_ok=True)
    for key, (_chapter, _tp, _te, body_pl, body_en) in TOPICS.items():
        body = body_pl if lang == "pl" else body_en
        with open(os.path.join(lang_dir, f"{key}.md"), "w", encoding="utf-8") as f:
            f.write(body)

# Chapters + topic order + titles, read by project_panels.HelpPanel -
# one shared manifest so the generator and the panel can never disagree
# about what topics exist, which chapter they belong to, or what order
# they appear in.
lines = ["# Auto-generated by generate_help.py - do not edit by hand.", "CHAPTERS = ["]
for chapter_key, title_pl, title_en in CHAPTERS:
    lines.append(f"    ({chapter_key!r}, {title_pl!r}, {title_en!r}),")
lines.append("]")
lines.append("")
lines.append("# (key, title_pl, title_en, chapter_key)")
lines.append("TOPICS = [")
for key, (chapter, title_pl, title_en, _bp, _be) in TOPICS.items():
    lines.append(f"    ({key!r}, {title_pl!r}, {title_en!r}, {chapter!r}),")
lines.append("]")
with open(os.path.join(OUT_DIR, "_manifest.py"), "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")

print(f"generated {len(TOPICS)} topics x 2 languages = {len(TOPICS) * 2} files, plus _manifest.py")
