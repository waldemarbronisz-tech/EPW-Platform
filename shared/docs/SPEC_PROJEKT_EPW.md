# Format pliku projektu EPW — kontrakt Studio — runtime

Wersja robocza do zatwierdzenia. Po zatwierdzeniu trafia do
`shared/docs/` i staje się obowiązująca dla obu programów.

---

## Zasada nadrzędna

**Projekt opisuje, co urządzenie ma robić. Nigdy w jakim jest stanie.**

Dzisiejszy `runtime/project.json` łamie tę zasadę: w jednym rekordzie
siedzi `warning_threshold` (nastawa, należy do projektu) obok `closes`,
`opens`, `closed_seconds`, `closed_since` (liczniki rosnące same,
należą do stanu).

To nie jest drobiazg estetyczny. To **przyczyna** tego, że skrypty
weryfikacyjne brudziły plik projektu — bo plik projektu zmieniał się
sam z siebie, w trakcie pracy. Rozcięcie tych dwóch rzeczy usuwa całą
klasę problemu.

Konsekwencja: **dwa pliki, nie jeden.**

| Plik | Zawartość | Kto zapisuje |
|---|---|---|
| `projekt.epw` | projekt — co ma robić | Studio (i runtime dla nastaw) |
| `runtime_state.json` | stan — liczniki, uzbrojenie, wykluczenia | wyłącznie runtime |

Plik stanu **nigdy nie trafia do repozytorium projektu** i nigdy nie
jest przenoszony między urządzeniami.

---

## Trzy warstwy dostępu

Rozstrzygnięte wcześniej, tu tylko zapisane, bo format musi to
odzwierciedlać.

| Warstwa | Co to jest | Gdzie się edytuje |
|---|---|---|
| **Struktura** | co w ogóle istnieje: karty, punkty, aparaty, strefy, ekrany, logika | **tylko Studio** |
| **Nastawa** | liczba w istniejącej rzeczy: próg, zwłoka, czas nadzoru | **Studio i runtime** (Engineer, z wpisem do dziennika) |
| **Obsługa** | uzbrój, rozbrój, wyklucz linię, tryb chodzenia | **tylko runtime**, nie należy do projektu |

Runtime traci **kreatory** — nie da się na panelu wymyślić nowej strefy
ani nowego punktu. Zachowuje **nastawy** — bo od tego jest narzędziem
nastawczym dla ADA01 i bo stoisz przy szafce z tabletem, nie z laptopem.

---

## Struktura pliku `projekt.epw`

### Nagłówek

```
format          "EPW_PROJECT_FILE"   (stała, obowiązkowa)
schema_version  1                     (liczba)
project         nazwa, opis, autor, daty utworzenia i zmiany
```

⚠️ **Nazwa `EPW_PROJECT_FILE` jest celowo różna** od `EPW_PROJECT`
z martwego `ProjectV2Schema.ts` w edytorze. Tamten szkic nadal leży
w repozytorium i myli — nie chcemy trzeciej rzeczy o tej samej nazwie.

### Skład urządzenia

```
modules  lista nazw modułów wchodzących w skład tego sterownika
```

To **nie jest lista przełączników**. To skład urządzenia, ustalany raz,
przy zakładaniu projektu. Sterownik podlewania nie ma alarmówki tak samo,
jak nie ma jej termostat — nie jako brak, tylko jako fakt.

**Runtime nie wie, że coś jest "wyłączone".** Wie tylko, z czego się
składa. Moduł spoza listy nie startuje wcale — nie zajmuje pamięci,
nie liczy, nie może wysterować wyjścia przez pomyłkę.

**Wymóg dla runtime:** przy wczytaniu projektu sprawdzić, czy logika
albo ekrany nie odwołują się do sygnałów modułu, którego nie ma
w składzie. Rozjazd = **jasny komunikat przy starcie**, nie ciche
niezadziałanie o trzeciej w nocy.

### Sprzęt

**Karty definiuje się RAZ, w projekcie.** Wszystko inne (Logic Studio,
Synoptic Editor) tylko je czyta — most, nie własna kopia z prawem
istnienia niezależnie od tego, co jest tutaj. Dodanie karty w Studio ma
być od razu widoczne jako dostępny adres wszędzie indziej; usunięcie
karty ma być od razu widocznym błędem (nie cichym skasowaniem bloku)
wszędzie, gdzie ktoś do niej się odwoływał.

```
cards      id (nadane przez użytkownika), model, kanały (rodzaj -> liczba kanałów), lokalizacja
locations  kod (prefiks), opis
```

Przykład karty (jeden rodzaj — najczęstszy przypadek): `id: "DI1", model: "ELA01", channel_kinds: {"DI": 32}, location: "KOT"`
Przykład karty (moduł mieszany — np. ELA z wejściami cyfrowymi i analogowymi na jednej fizycznej karcie): `id: "ELA1", model: "ELA01", channel_kinds: {"DI": 8, "AI": 4}, location: "KOT"`
— jedna karta to jeden fizyczny moduł: jedno id, jeden adres Modbus, jedna lokalizacja, niezależnie od tego, ile rodzajów kanałów ma na pokładzie.

**Sterownik Modbus w runtime (zrealizowane 2026-09-15).** `modbus_bus`
z projektu (RTU: port, prędkość, parzystość; TCP: host, port) i
`modbus_unit_id` kart obsługuje `runtime/epw_os/drivers/modbus_driver.py`
— czysta biblioteka standardowa (FC2 dla DI, FC1/FC5 dla DO, FC4 dla AI —
surowa wartość rejestru, przeliczana jak dotąd przez `analog_scaling`,
FC6 dla AO; kanał n = adres n-1). KTÓRY sterownik I/O pracuje, to
ustawienie sterownika, nie projektu — `controller.local.json`:

```
"io_driver": {"driver": "MODBUS", "poll_interval_ms": 250, "timeout_s": 1.0,
              "retries": 1, "ai_signed": false, "read_back_outputs": true}
```

Bez tej sekcji działa symulator, dokładnie jak dotąd. Karta bez
`modbus_unit_id` nie jest odpytywana i dostaje problem startowy; magistrala
RTU wymaga pakietu `pyserial` (import opcjonalny — bez niego sterownik
startuje i zgłasza problem startowy, TCP działa bez niczego). Do sprawdzenia
mapowania na prawdziwej karcie służy `runtime/tools/modbus_probe.py` (ta sama
biblioteka co sterownik: odczyt DI/DO/AI po unit id, zapis cewki/rejestru,
pętla odczytów).
Przykład lokalizacji: `code: "KOT", description: "Kotłownia"`

**Karty rodzą punkty.** Dodajesz kartę o 32 kanałach — powstaje 32 pustych
punktów. Nie wpisujesz ich ręcznie.

**Lokalizacja karty to gdzie stoi MODUŁ** (szafka), nie gdzie idą jego
zaciski — jedna karta w szafce potrafi obsługiwać kotłownię, piwnicę
i bramę naraz. Jest tylko DOMYŚLNĄ lokalizacją dla własnych punktów
karty (patrz niżej) — zmiana lokalizacji karty nigdy nie nadpisuje
punktu, któremu użytkownik ustawił własną.

**Lokalizacje dają prefiks**, który gwarantuje unikalność identyfikatorów
aparatów w całym projekcie. `KOT_KMG1` i `MH_KMG1` to dwa różne aparaty.
`KOT_KMG1` w dwóch plikach ekranów to zawsze ten sam.

### Punkty — rejestr zacisków

```
points
  address         "DI1.DI.1"      — <id_karty>.<RODZAJ>.<KANAŁ>
  description     opis zacisku
  location        kod lokalizacji, LUB brak (puste) — patrz niżej
  technical_note  wolny tekst dla serwisanta
```

**Lokalizacja punktu dziedziczy z karty domyślnie.** `location` puste
(brak wartości) = punkt pokazuje lokalizację swojej karty. Punkt
z WŁASNĄ, jawnie ustawioną lokalizacją (włącznie z jawnie pustą —
"ten zacisk naprawdę nie ma lokalizacji, mimo że karta ma") zawsze
wygrywa z tym, co dziedziczy. Rozróżnienie "brak = dziedzicz" od "pusty
tekst = jawnie brak" jest tym, co pozwala zmienić lokalizację karty bez
nadpisania punktów, którym ktoś już wpisał własną — nie osobną flagą,
tylko samym brakiem wartości. Większość punktów jednej karty faktycznie
idzie w to samo miejsce; wyjątki dostają własną, jawną wartość.

Dla punktów analogowych dodatkowo (pola przeniesione żywcem
z dzisiejszego `analog_points`, bo działają):

```
  signal_type   4-20mA / 0-10V / 0-3.3V ADC / wartość gotowa
  raw_min, raw_max, eng_min, eng_max
  unit, decimals
```

**Adresacja jest kartowa.** Runtime porzuca `DI1..DI64`. Powód
zmierzony w `ADDRESSING_INVENTORY.md`: druga karta wejść nie ma dokąd
pójść, bo nie istnieje `DI65`, a przykładowy projekt już ma trzy karty.
Most tylko odsuwa tę samą robotę.

**Notatka techniczna nie ma znaczenia funkcjonalnego.** Program jej nie
używa. Jest dla człowieka, który za dwa lata otworzy szafkę i musi
wiedzieć, że to jest zacisk X2:14, przewód LiYCY 2×0,75.

### Aparaty

```
devices  (dokładnie jak dziś w .epwsyn — pole devices)
  id            "KOT_KMG1"
  behavior      SWITCHED | SIGNAL | MEASURED | MODULATED | SELECTOR
  kind          etykieta bez znaczenia funkcjonalnego
  feedback      które punkty czyta (pierwszy = styk ZAŁĄCZONY)
  command       które punkty steruje (pierwszy = ZAŁĄCZ, drugi = WYŁĄCZ)
  commandStyle  MAINTAINED | PULSE | PULSE_TOGGLE   (tylko SWITCHED)
  pulseMs       czas impulsu [ms] dla PULSE / PULSE_TOGGLE
  supervision   czasy nadzoru
  safeState     onStartup, onLinkLoss
```

**Styl sterowania mówi, JAK wyjścia napędzają aparat** — bo to samo
"jedno DO" może być cewką trzymaną pod napięciem albo impulsem:

- `MAINTAINED` — poziom: zasilone = ZAŁĄCZONE (jedna cewka), albo jedna
  cewka na kierunek trzymana pod napięciem (dwa wyjścia; runtime zwalnia
  przeciwną cewkę przed zasileniem żądanej).
- `PULSE` — impuls `pulseMs` na kierunek, osobne cewki; przy jednym
  wyjściu sterowany jest tylko ZAŁĄCZ.
- `PULSE_TOGGLE` — **przekaźnik impulsowy jednocewkowy** (klasa R15/3P):
  jedna cewka za jednym lub dwoma wyjściami (typowo DO "na załącz" i DO
  "na wyłącz" plus lokalne przyciski, wszystkie na tę samą cewkę). Każdy
  impuls przełącza, obojętnie skąd przyszedł — dlatego runtime podaje
  impuls **tylko gdy `feedback[0]` mówi, że aparat nie jest już w
  żądanym stanie**; inaczej przełączyłby go w drugą stronę. Sprzężenie
  zwrotne jest obowiązkowe, Studio ("Sprawdź projekt") i Synoptic
  odrzucają `PULSE_TOGGLE` bez niego.

**Aparat zużywa punkty.** Punkt zajęty przez jeden aparat nie może być
przypisany do drugiego — Studio ma to wykryć przy przypisaniu, nie przy
uruchomieniu.

Nie każdy punkt należy do aparatu. Czujka, licznik impulsów, wolne
wejście na przyszłość istnieją same z siebie.

**Jeden zacisk = jeden adres = jedna nazwa w całym projekcie.**

Rejestr punktów zna dokładnie cztery rodzaje: `DI`, `DO`, `AI`, `AO`.
Nic więcej nie istnieje — nie ma osobnych bytów typu "styk pomocniczy",
"cewka", "sprzężenie zwrotne". To etykiety w głowie serwisanta, nie
osobne wpisy w rejestrze.

Aparat **nie tworzy nowych nazw**. Pola `feedback`/`command` przechowują
**adresy z rejestru punktów** — to wskazanie (referencja), nigdy kopia
ani pochodna. `KOT_KMG1` jako id aparatu i `DI1.DI.1` jako adres punktu,
który ten aparat czyta, to dwie oddzielne rzeczy; jedna nie generuje
drugiej.

**Zakazane:** adresy pochodne typu `KOT_KMG1.feedback`, `KOT_KMG1.coil`
i podobne — cokolwiek, co doklejałoby własność aparatu do jego id
zamiast wskazać istniejący adres z rejestru punktów. Gdy coś potrzebuje
wiedzieć, którym wejściem aparat jest obserwowany, pyta rejestr
aparatów o jego pole `feedback` i dostaje `DI1.DI.5` — ten sam ciąg,
którym posługuje się reszta platformy (Studio, Synoptic, runtime,
Logic Studio). Ta sama zasada co przy sygnałach nadzoru i przy
klasyfikacji po zachowaniu: jedno źródło prawdy, bez równoległych
słowników.

### Ekrany — osadzone w projekcie

```
screens
  name     nazwa pokazywana operatorowi
  order    kolejność przełączania
  canvas   wymiary i tło
  objects  obiekty graficzne (jak dziś w .epwsyn)
```

**Ekrany są W ŚRODKU pliku projektu**, nie osobnymi plikami.
Decyzja z 2026-09-10: jeden plik `projekt.epw`, koniec.

To usuwa problem u źródła. Cztery ekrany w czterech plikach = cztery
kopie rejestru aparatów, które muszą się rozjechać. Jeden plik = jedna
prawda, nie ma czego synchronizować.

**Obiekt ekranu niesie tylko grafikę i `deviceId`.** Zero konfiguracji
aparatu — ta mieszka w `devices`, raz na projekt.

Struktura obiektu pozostaje **identyczna** jak w dzisiejszym `.epwsyn`.
Czytnik napisany w `epwsyn_loader.py` działa bez zmian — zmienia się
tylko to, skąd bierze dane: z sekcji projektu zamiast z osobnego pliku.

`.epwsyn` zostaje jako **format wymiany** — do wysłania komuś jednego
ekranu, do zaimportowania cudzego. Nie jest źródłem prawdy dla projektu.

### Logika — osadzona w projekcie

```
logic          źródło logiki (EPW_LOGIC — bloki i przewody, edytowalne w Logic Studio)
logic_runtime  skompilowana logika (EPW_RUNTIME_LOGIC, jak w .epwlogic.runtime.json) — to wykonuje runtime
```

Tak samo jak ekrany — w środku pliku, nie obok.

**Zrealizowane 2026-09-15** (zgłoszenie: „tworząc synoptykę w projekcie i
zapisując projekt na głównym pasku, synoptyka nie zapisuje się [...] dalej
to traktowane jest jako osobne programy"). Zapisz na górnym pasku Studio
zbiera dokumenty obu edytorów do `screens` / `logic` / `logic_runtime`
(`logic_runtime` odświeżane przy każdym zapisie, gdy logika się
kompiluje); Otwórz/Nowy oddają je edytorom; niezapisana praca w edytorze
liczy się jako niezapisana praca projektu. Runtime bierze `logic_runtime`
i `screens` z projektu; ścieżki `.epwlogic.runtime.json` / `.epwsyn` w
`controller.local.json` zostają wyłącznie jako zapas dla projektu
zapisanego wcześniej. `.epwsyn` / `.epwlogic` to nadal formaty wymiany.

**Runtime rysuje osadzony ekran (zrealizowane 2026-09-15, etap pierwszy).**
Strona *Widok główny → Synoptyka* rysuje `screens` na żywo:
`runtime/epw_os/gui/synoptic/`. Symbole pochodzą z pliku
`shared/symbols/geometry.json` — całej biblioteki Edytora Synoptyki
wyeksportowanej jako prymitywy rysunkowe (`studio/synoptic/tools/geometry_export`,
`npm install && npm run export` po każdej zmianie biblioteki; test runtime
porównuje plik z rejestrem symboli). Stan symbolu bierze się z aparatu
(`deviceId` → `devices` → `feedback[0]`), wartości z tagów; kliknięcie
aparatu SWITCHED wysyła `<id>.CLOSE` / `<id>.OPEN` tą samą drogą co
schemat jednokreskowy. Od 2026-09-17 przewody mają kolor według sieci
(port `NetResolver.ts`: sieć jest zasilana z punktu granicznego SOURCE albo
z zacisku OUT aparatu załączonego według potwierdzenia na żywo), węzły mają
kropki, symbole wodne rysują wariant „sieć aktywna", wentylator się obraca.
Jeszcze nie na żywo: cieniowanie ścian.

**Widok główny (schemat jednokreskowy) po `deviceId`** — role Q1/KMG/KM1/
KM2/KVG1 wiąże `apparatus.bind_roles_from_screens()`: obiekt ekranu z
`deviceId`, którego aparat w `screens.devices` ma oznaczenie roli,
wskazuje aparat; reguła nazewnicza zostaje tylko dla ról, których ekran nie
rysuje.

**Rejestr aparatów: Studio ↔ Synoptic — jedna lista.** Aparat w Studio
(płaski: `feedback`/`command`/`commandStyle`) i aparat w Synoptic
(`DeviceSchema.ts`: `diClosed`/`doClose`/...) opisują to samo;
`project_panels.device_to_synoptic_dict()` / `device_from_synoptic_dict()`
tłumaczą, a synchronizacja przy otwarciu edytora jest — jak dla kart i
lokalizacji — tylko dodająca (nic nie nadpisuje, nic nie usuwa). Aparat
wypchnięty ze Studio dostaje oznaczenie z id (`KOT_KM1` → `-KM1`) i nazwę
równą id; Synoptic zachowuje własne bogatsze pola aparatów, które już ma.

### Alarmówka *(tylko gdy moduł jest w składzie)*

```
intrusion
  zones     strefy, ich nazwy i przypisanie linii
  lines     typ linii (EOL/DEOL), punkt, opóźnienia
  timings   czas na wyjście, czas na wejście, czas sygnalizacji
```

Struktura tylko w Studio. Nastawy czasów w obu. Uzbrajanie,
rozbrajanie, wykluczanie linii — **to stan, nie projekt.**

### Nastawy zabezpieczeń *(tylko gdy moduł jest w składzie)*

```
protection  progi, zwłoki, blokady
```

To są **nastawy do wgrania do ADA01**, nie logika zadziałania.
Zabezpieczenie realizuje ADA01 samodzielnie, runtime jest narzędziem
nastawczym. Zasada "ekran informuje, sprzęt chroni" pozostaje nienaruszona.

---

## Wersjonowanie — plik na sterowniku ŻYJE

Runtime zapisuje zmienione nastawy z powrotem do `projekt.epw`,
żeby dało się ściągnąć plik ze sterownika na komputer i zobaczyć,
co faktycznie w nim siedzi.

To znaczy, że plik na sterowniku **zmienia się bez udziału Studio** —
i powstaje scenariusz do rozbrojenia:

> Zmieniasz próg na panelu. Tydzień później dorysowujesz ekran
> w Studio i wgrywasz projekt. Nastawa sprzed tygodnia znika
> po cichu, a zabezpieczenie działa według innej wartości niż myślisz.

**Wymagane pola nagłówka:**

```
revision        liczba, rosnąca przy KAŻDYM zapisie
modified_at     znacznik czasu
modified_by     "studio" albo "panel"
settings_hash   suma kontrolna samych nastaw
```

**Wymóg dla Studio:** przed wgraniem projektu na sterownik odczytać
`revision` z urządzenia. Jeśli tam jest **nowsza** — ZATRZYMAĆ SIĘ
i pokazać, co się rozjechało (tu 25 A, tam 40 A), zamiast nadpisać.

To ten sam mechanizm, który zaprojektowałeś dla ADA01 — numer wersji,
suma kontrolna, rozjazd = alarm. Tylko o poziom wyżej.

**Zrealizowane 2026-09-17.** `settings_hash` liczy `project_format.settings_hash()`
(SHA-256 z `settings_snapshot()` — same nastawy: opóźnienia stref, parametry
linii, progi zabezpieczeń procesowych, nastawy stopni elektrycznych, skalowanie
punktów AI, próg ostrzegawczy licznika łączeń punktu DI, nadzór zasilania; lista pól `SETTING_FIELDS` jest ta sama, którą
runtime stosuje do rozdziału nastawa/struktura) i trafia do nagłówka pliku przy
każdym zapisie. Runtime podaje go w `GET /api/v1/project`, a same wartości w
`GET /api/v1/project/settings`. Studio (*Sterownik → Wyślij do urządzenia*):
zapisuje projekt, czyta nagłówek sterownika, przy innym `settings_hash` pokazuje
tabelę rozjazdów (nastawa, Studio, sterownik) i pyta, czy nadpisać; wysyła plik
`POST /api/v1/project/install?expected_revision=N` (token Engineer) — sterownik
odmawia (409), gdy jego rewizja zmieniła się w międzyczasie, instaluje plik
(poprzedni jako `.bak`, znacznik `projekt.epw.pending`) i po odpowiedzi kończy
proces kodem 3, a `systemd` (`Restart=on-failure`) uruchamia go z nowym
projektem. Jeśli nowy plik zostanie odrzucony przy tym starcie, wraca `.bak`,
odrzucony plik zostaje jako `.rejected`, a panel zgłasza problem startowy.
*Zgraj z urządzenia* pobiera `GET /api/v1/project/file` (token Engineer) i
otwiera go jak *Plik → Otwórz*.

---

## Plik stanu — `runtime_state.json`

Wszystko, co zmienia się samo w trakcie pracy:

```
switching_counters   closes, opens, closed_seconds, closed_since
intrusion_state      co uzbrojone, co wykluczone, pamięć alarmu
last_screen          ostatnio otwarty ekran
```

Zapisywany wyłącznie przez runtime. Nie wchodzi do repozytorium.
Nie przenosi się między urządzeniami. Utrata pliku stanu jest
**nieszkodliwa** — urządzenie wstaje z domyślnymi.

⚠️ **Wyjątek: stan uzbrojenia alarmówki.** Rozstrzygnięte 2026-09-10:
po zaniku zasilania wraca do stanu sprzed. Uzbrojona wstaje uzbrojona,
rozbrojona — rozbrojona.

**Wymóg wynikający wprost:** zapis stanu uzbrojenia musi być
**natychmiastowy przy każdej zmianie**, nie przy zamknięciu programu
ani co minutę. Inaczej zanik zasilania dwie minuty po uzbrojeniu
przywróci stan rozbrojony i nikt się nie dowie.

To jedyny element stanu, którego utrata jest szkodliwa.

---

## Czego w formacie NIE MA — świadomie

**Wzorców i profilów urządzeń.** Każda instalacja jest inna, katalog
byłby półką, na którą nikt nie zagląda.

**Motywów wizualnych.** Studio ma jedną szatę. Runtime ma swoje motywy
i to jego sprawa, nie projektu.

**Mapowania adresów na stare `DI1..DI64`.** Migracja, nie most.

**Dziedziczenia i szablonów aparatów.** "Bez automatycznych szablonów"
oznacza, że program nie wypełnia nic sam.

---

## Migracja z dzisiejszego stanu

`tag_descriptions` i `output_descriptions` w dzisiejszym `project.json`
są **puste** (zweryfikowane). Nie ma czego przenosić.

Do przeniesienia jest wyłącznie `analog_points` — 16 rekordów.
To **jednorazowy skrypt importujący**, nie część kontraktu. Format nie
musi na zawsze znać starej postaci.

---

## Kolejność wdrożenia

1. **Czytnik formatu w Studio** — zakładanie i zapis projektu
2. **Rejestr punktów w Studio** — karty rodzą punkty, opisy
3. **Runtime czyta `projekt.epw`** — zamiast dzisiejszego `project.json`
4. **Rozcięcie stanu** — `runtime_state.json` osobno
5. **Migracja adresacji** na kartową
6. **Runtime traci edycję opisów** — strona DI/DO staje się diagnostyką
7. **Alarmówka** — struktura do Studio, obsługa zostaje w runtime

Zasada niezmienna przy każdym kroku: **najpierw Studio zyskuje, potem
runtime traci.** Nigdy odwrotnie — inaczej powstaje okno czasu,
w którym czegoś nie da się skonfigurować nigdzie.

---

## Studio — sterownik — połączenie na żywo

Studio łączy się ze sterownikiem przez **istniejące REST API**
(uwierzytelnianie tokenem, ten sam mechanizm co dla HAOS). Nie trzeba
budować nowego kanału — trzeba wykorzystać ten, który już działa.

### Podgląd nastaw i wykrywanie rozjazdu

Studio pokazuje nastawy odczytane z urządzenia **obok** tych z projektu
i zaznacza różnice. To główny sposób wykrywania rozjazdu — pokazuje
problem wtedy, kiedy jeszcze można coś z nim zrobić, zamiast ostrzegać
w momencie wgrywania.

To ta sama zasada, którą zaprojektowano dla ADA01: urządzenie samo się
opisuje, narzędzie porównuje, rozjazd = alarm.

⚠️ **Numer wersji w pliku zostaje** jako zabezpieczenie na wypadek pracy
bez połączenia — sterownik za VPN-em, sieć padła, projekt edytowany
w domu. Porównanie na żywo działa tylko wtedy, gdy połączenie jest.

### Co jeszcze daje ten kanał

- żywe stany przy punktach podczas projektowania ekranu
- weryfikacja, czy karta o danym adresie w ogóle odpowiada
- zdalna diagnostyka bez chodzenia do szafki

### Wymuszanie stanów — dozwolone, obwarowane

Sprawdzone wobec praktyki branżowej (TIA Portal, 2026-09-10): narzędzia
projektowe **standardowo wymuszają stany wejść i wyjść** — Force Table
zapisuje wartości nadpisujące logikę programu. Siemens obudowuje to
warstwami zabezpieczeń: dostęp do rzeczywistych wyjść jest domyślnie
zablokowany i wymaga jawnego odblokowania, wymuszone wartości są
wyróżnione kolorem, wszystkie da się zdjąć jednym poleceniem,
a **sygnały bezpieczeństwa wymuszaniu nie podlegają**.

To ostatnie jest dokładnie zasadą "ekran informuje, sprzęt chroni",
wypowiedzianą przez producenta sterowników.

**Zasada dla EPW:**

> Studio może wymuszać stany do uruchamiania i testów. Nigdy nie sięga
> toru zabezpieczeniowego. Wymuszenie jest zawsze widoczne i zawsze da
> się je zdjąć jednym ruchem.

Trzy warunki, spełnione **łącznie**:

1. **Domyślnie wyłączone.** Jawne wejście w tryb wymuszania, poziom
   Engineer, wpis do dziennika audytowego. Nie przypadkowy klik.
2. **Widoczne po obu stronach.** Nie tylko w Studio — także **na panelu
   przy szafce**. Człowiek stojący przy urządzeniu musi wiedzieć, że
   ktoś steruje nim zdalnie. To dodatek wobec wzorca Siemensa,
   konieczny, bo panel EPW stoi przy szafce, nie w sterowni.
3. **Zdjęcie wszystkiego jednym poleceniem** oraz automatyczne przy
   zerwaniu połączenia i przy restarcie. Wymuszenie, które przeżywa
   zamknięcie laptopa, to najgorszy możliwy stan instalacji.

**Czego wymuszać NIE WOLNO:** niczego, co należy do toru
zabezpieczeniowego. ADA01 ma własną drogę do cewki wyłączającej
i żadne narzędzie projektowe tam nie sięga — ani przez Modbus,
ani przez API, ani w trybie serwisowym.

**Powiązanie:** ta sama mechanika obsługuje "wewnętrznego Omicrona" —
test zabezpieczeń to wymuszenie stanu, pomiar czasu zadziałania
i raport. Jeden mechanizm, dwa zastosowania.

---

## Rozstrzygnięte 2026-09-10

1. **Stan uzbrojenia po zaniku zasilania** — wraca do stanu sprzed
2. **Jeden plik czy katalog** — jeden plik, `projekt.epw`
3. **Gdzie runtime zapisuje nastawy** — do `projekt.epw`, z numerem
   wersji i ochroną przed nadpisaniem (patrz: Wersjonowanie)
4. **Studio łączy się ze sterownikiem** — tak, przez REST API;
   podgląd nastaw na żywo z zaznaczeniem różnic
5. **Wymuszanie stanów ze Studio** — dozwolone przy trzech warunkach,
   nigdy w torze zabezpieczeniowym (patrz: Studio — sterownik)
