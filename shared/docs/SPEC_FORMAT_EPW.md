# SPECYFIKACJA FORMATU `.epw`

**Wspólny format projektu platformy EPW**
Wersja specyfikacji: 1.0 · 2026-09

> Ten dokument jest **kontraktem między trzema aplikacjami**.
> Musi być znany w każdym czacie roboczym: EPW-OS, Synoptic Editor,
> Logic Studio. Zmiana formatu wymaga uzgodnienia we wszystkich trzech.

---

# 1. Po co to jest

Dziś projekt EPW rozsypany jest po kilku miejscach: `project.json`
w katalogu OS-a, pliki `.epwsyn` z edytora grafiki, skompilowana logika
z Logic Studio. Przeniesienie projektu na inny sterownik oznacza
zebranie tego ręcznie i nadzieję, że nic nie zostało pominięte.

Format `.epw` to **jeden plik, który niesie cały projekt**.

Wgrywasz go do sterownika i masz wszystko: ekrany, logikę, aparaty,
nastawy, konfigurację.

---

# 2. Czym jest fizycznie

**Zwykłe archiwum ZIP o ustalonej strukturze wewnętrznej**, z rozszerzeniem
`.epw`.

Tak samo działają pliki pakietów biurowych. Użytkownik widzi jeden plik,
a w środku jest katalog z osobnymi częściami.

Zalety takiego wyboru:
- każda część jest osobnym plikiem — da się obejrzeć bez programu
- kompresja: projekt z wieloma ekranami zajmuje mało
- narzędzia do ZIP są w każdym języku, zero nowych zależności
- da się dołożyć nową część bez psucia starych czytników

---

# 3. Struktura wewnętrzna

```
konfiguracja.epw
│
├── manifest.json              ← ZAWSZE PIERWSZY, opisuje resztę
│
├── project/
│   ├── metadata.json          ← nazwa, opis, lokalizacja, autor, daty
│   ├── devices.json           ← lista urządzeń polowych (ELA, ADA, EPM)
│   └── apparatus.json         ← LISTA APARATÓW (wariant B)
│
├── io/
│   ├── digital_inputs.json    ← opisy i konfiguracja wejść
│   ├── digital_outputs.json   ← opisy i konfiguracja wyjść
│   └── analog_points.json     ← punkty analogowe ze skalowaniem
│
├── screens/
│   ├── index.json             ← lista ekranów, kolejność, ekran startowy
│   ├── main.epwsyn            ← ekrany z Synoptic Editora
│   └── <kolejne>.epwsyn
│
├── logic/
│   ├── project.epwlogic       ← projekt źródłowy (edytowalny)
│   └── runtime.json           ← wersja skompilowana (wykonywalna)
│
├── protection/
│   ├── electrical.json        ← zabezpieczenia elektryczne
│   └── process.json           ← zabezpieczenia procesowe
│
├── security/
│   ├── zones.json             ← strefy systemu alarmowego
│   ├── lines.json             ← linie dozorowe
│   └── power_supervision.json ← nadzór zasilania
│
└── settings/
    ├── features.json          ← które funkcje włączone
    ├── navigation.json        ← układ i widoczność menu
    ├── mqtt.json              ← konfiguracja MQTT BEZ HASŁA
    └── localization.json      ← język, format daty
```

Katalogi nieużywane w danym projekcie mogą nie istnieć. Czytnik ma to
znieść bez błędu.

---

# 4. `manifest.json` — obowiązkowy

Pierwsza rzecz, którą czyta każda aplikacja. Bez niego plik jest
nieważny.

Musi zawierać:

| Pole | Znaczenie |
|---|---|
| `format` | Stały znacznik `"EPW_PROJECT"` — potwierdza, że to nasz plik |
| `format_version` | Wersja **formatu**, nie projektu. Patrz rozdział 6 |
| `project_id` | Identyfikator projektu, niezmienny przez całe życie |
| `created_at` / `modified_at` | Znaczniki czasu w UTC |
| `created_by` | Która aplikacja i w jakiej wersji utworzyła plik |
| `contents` | Lista części obecnych w archiwum |
| `checksums` | Suma kontrolna każdej części |

**Suma kontrolna jest obowiązkowa.** Uszkodzony plik ma zostać wykryty
przy wczytaniu, a nie objawić się dziwnym zachowaniem sterownika trzy dni
później.

---

# 5. 🔴 Co jest w pliku, a co zostaje na urządzeniu

**To jest najważniejszy rozdział tej specyfikacji.**

## W PLIKU `.epw` — projekt, czyli to, co zaprojektowałeś

Lista aparatów · ekrany synoptyczne · projekt i runtime logiki · definicje
punktów analogowych · opisy wejść i wyjść · strefy i linie alarmowe ·
nastawy zabezpieczeń · konfiguracja funkcji · układ nawigacji ·
konfiguracja MQTT bez hasła · język

Wspólne dla wszystkich sterowników, na które wgrasz ten projekt.

## NA URZĄDZENIU — eksploatacja i sekrety

**Sekrety, nigdy w pliku projektu:**
- skróty PIN-ów (`access.local.json`)
- token API (`api_tokens.local.json`)
- hasło do brokera MQTT (`mqtt.local.json`)

**Dane eksploatacyjne, opisujące TEN konkretny obiekt:**
- liczniki łączeń aparatów
- historia serwisowa (notatki)
- baza Historiana
- dziennik audytowy
- historia alarmów
- pamięć alarmu włamaniowego
- stan okna, rozwinięcie drzewa nawigacji, wybrany motyw

### Dlaczego to rozdzielenie jest krytyczne

Wgrywasz projekt z rozdzielnicy A na sterownik B. Jeśli liczniki łączeń
pojechałyby razem z projektem, **sterownik B twierdziłby, że jego stycznik
przełączał się 4000 razy** — a on jest nowy.

To samo z notatkami serwisowymi: „wymieniony 03.2026, styki przepalone"
dotyczy aparatu w rozdzielnicy A, nie w B.

Dziennik audytowy tym bardziej — opisuje, kto co robił na tamtym
urządzeniu.

### ⚠️ Dziś to jest wymieszane

`project.json` w obecnej postaci zawiera **jednocześnie konfigurację
i dane eksploatacyjne** — liczniki łączeń i notatki serwisowe siedzą
w tym samym pliku, co opisy i punkty analogowe.

Skutek widoczny na co dzień: **plik projektu zmienia się przy każdym
uruchomieniu programu**, bo liczniki rosną. Śmieci w gicie i brak
możliwości odróżnienia „zmieniłem konfigurację" od „program chodził".

**Wdrożenie formatu `.epw` musi to rozdzielić.** To nie jest zmiana
kosmetyczna — bez niej cały format traci sens.

---

# 6. Wersjonowanie i zgodność

`format_version` to **wersja formatu**, nie wersja projektu ani programu.

**Zasady:**

Aplikacja **odmawia wczytania** pliku o wersji formatu **nowszej** niż
obsługiwana. Odmawia jawnie, z komunikatem — nie próbuje zgadywać.

Aplikacja **wczytuje** pliki starszych wersji, uzupełniając brakujące
części wartościami domyślnymi. Migracja przy zapisie, nie przy odczycie.

Nowa część archiwum **nie podnosi** wersji formatu, jeśli stare czytniki
mogą ją bezpiecznie pominąć. Podnosi ją tylko zmiana, która psuje
zgodność.

---

# 7. Zasady dla zawartości

## Nazwy tagów

Obowiązuje **konwencja zgodna z kodem EPW-OS**:
`Security.` · `Safety.` · `System.` · `Process.` · `Device.` · `Cabinet.` ·
`Meas.` · `Sim.` · `Marker.` · `Link.` · `Request.`

Pełne słowa, nie skróty. Człony w notacji z wielkiej litery
(`Security.Zone.Z1.Armed`).

Szczegóły w rejestrze sygnałów (arkusz `EPW_Rejestr_Bitow_Wewnetrznych`).

## Tożsamość obiektów

Każdy obiekt — aparat, punkt, strefa, linia, ekran — ma **stabilny
identyfikator**, niezależny od nazwy nadanej przez człowieka.

**Zmiana nazwy nie może zmieniać powiązań.** Ekrany i logika wiążą się
po identyfikatorze, nie po nazwie wyświetlanej.

## Adresy fizyczne

Docelowo `ELA01.DI01`, `ADA01.DO01`, `EPM01.UL1.RMS` — z jawnym
wskazaniem urządzenia. Nie globalne `DI01`, bo przy drugim module
komunikacji nazwy się zderzą.

## Lista aparatów — wariant B

Konfiguracja aparatu **nie siedzi w pliku ekranu**. Ekran mówi tylko:
„w tym miejscu, tym symbolem, pokaż aparat KMG".

Aparat zdefiniowany raz, w `project/apparatus.json`. Logic Studio i OS
zaglądają do tej samej listy.

---

# 8. Wczytywanie do sterownika

**Kolejność:**
1. Sprawdź `manifest.json` — format, wersja, sumy kontrolne
2. Odrzuć plik uszkodzony albo z nowszej wersji formatu, z komunikatem
3. Wczytaj listę urządzeń i aparatów
4. Wczytaj wejścia i wyjścia
5. Wczytaj zabezpieczenia i system alarmowy
6. Wczytaj ekrany
7. Wczytaj logikę
8. Zastosuj ustawienia

**Wymogi:**

Wczytanie ma być **atomowe**. Jeśli którakolwiek część zawiedzie —
sterownik zostaje przy poprzednim projekcie. Nie ma stanu „połowa
nowego, połowa starego".

Dane eksploatacyjne **przeżywają wczytanie projektu**. Liczniki, notatki
i historia zostają.

Fakt wczytania trafia do **dziennika audytowego**: kto, kiedy, jaki
projekt, jaka suma kontrolna.

Jeśli nowy projekt usuwa aparat, dla którego istnieją liczniki albo
notatki — **nie kasuj ich po cichu**. Ostrzeż i pozwól zdecydować.

---

# 9. Co musi zrobić każda aplikacja

**EPW-OS** — wczytać `.epw` w całości, zapisać z powrotem po zmianach
zrobionych na panelu, wyeksportować listę sygnałów dla pozostałych.

**Synoptic Editor** — czytać i zapisywać `screens/` oraz
`project/apparatus.json`, czytać listę sygnałów z OS-a.

**Logic Studio** — czytać i zapisywać `logic/`, czytać listę aparatów
i listę sygnałów.

**Każda aplikacja musi znieść plik zawierający części, których nie
rozumie**, i zachować je nietknięte przy zapisie. Inaczej otwarcie
projektu w Logic Studio skasowałoby ekrany.

---

# 10. Do rozstrzygnięcia

| # | Pytanie | Uwaga |
|---|---|---|
| 1 | Czy `.epw` ma być podpisany albo szyfrowany? | Chroni przed podmianą projektu, ale komplikuje |
| 2 | Czy przechowywać w pliku poprzednie wersje projektu? | Wygodne przy cofaniu zmian, powiększa plik |
| 3 | Jak wgrywać: pendrive, sieć, karta pamięci? | Wpływa na to, co trzeba zbudować w OS-ie |
| 4 | Czy sterownik ma umieć wyeksportować swój bieżący projekt? | Przydatne przy klonowaniu instalacji |
| 5 | Co przy wczytaniu projektu z innym `project_id`? | Zamiana projektu czy pomyłka operatora? |

---

# 11. Kolejność wdrożenia

1. **Rozdzielenie konfiguracji od danych eksploatacyjnych** w EPW-OS.
   Wymóg wstępny — bez tego reszta nie ma sensu.
2. **Format `apparatus.json`** — kontrakt trzech aplikacji.
3. **Zapis i odczyt `.epw`** w EPW-OS.
4. **Obsługa `.epw`** w Synoptic Editor i Logic Studio.
5. **Renderer `.epwsyn`** w EPW-OS.
6. **Moduł wykonujący logikę** w EPW-OS.
7. **Wspólny instalator** — na końcu, kosmetyka.
