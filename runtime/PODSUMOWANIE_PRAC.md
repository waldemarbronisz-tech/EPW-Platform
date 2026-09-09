# EPW-OS — podsumowanie wykonanych prac

Notatka obejmuje całą dotychczasową pracę nad EPW-OS w tej serii sesji.
Stan na moment wygenerowania: branch `feature/analog-points-manager`
(najnowsza praca), zbudowany na `main`, do którego wcześniej zmergowano
dwie wcześniejsze gałęzie (`feature/topology-fix-generic-devices` i
`feature/alarm-ack-csv-export-screen-sleep`). Wszystko w tym pliku odnosi
się do realnie zaimplementowanego, przetestowanego kodu — nie do planów.

---

## 1. System dostępu 3-poziomowego (User / Operator / Engineer)

- PIN-y nigdy w plaintext w kodzie/commitach — tylko skróty SHA-256 w
  gitignorowanym `epw_os/config/access.local.json`.
- Losowa generacja PIN-ów przy pierwszym uruchomieniu, jednorazowy
  komunikat w konsoli.
- Rozwijana lista wyboru poziomu dostępu w pasku górnym (User/Operator/
  Engineer) — zejście w dół bez PIN-u, wejście w górę przez prompt PIN.
- Auto-wylogowanie po 5 min bezczynności (niezależne od trybu wygaszania
  ekranu, patrz niżej).
- Formularz zmiany PIN w Settings: **stary PIN + nowy PIN + potwierdzenie**
  — autoryzacja przez znajomość starego PIN-u, nie przez aktualny poziom
  sesji (bezpieczniejsze: zostawiona odblokowana sesja Engineer nie
  wystarczy, żeby zmienić PIN bez jego znajomości).
- PIN-y operatora i inżyniera zresetowane na "1111" jako operacja na
  lokalnym pliku (przez istniejący `set_pin()`), nie jako zmiana kodu —
  wartość PIN-u nigdy nie trafiła do repozytorium.

## 2. Control Outputs — tabela 64-kanałowa (DO01-DO64)

- Przeprojektowane z kart na tabelę analogiczną do Digital Inputs.
- Rozszerzone z 4 do 64 kanałów (DO01-DO64), zachowując realne sprzężenie
  zwrotne DO01-DO04 z DI1-DI4.
- Przycisk "Force" (ręczne wymuszenie) — widoczny tylko dla Engineer,
  celowo mało wygodny (osobne okno potwierdzenia), routowany przez
  prawdziwy `CommandManager.request_command_ex()` → `safety_kernel` →
  `logic_engine` → `driver_manager`, zero obejścia.

## 3. "MAIN VIEW" (dawniej "ENTRY GATE")

Zmiana nazwy zakładki — docelowo ma hościć przełączalne ekrany
synoptyczne po integracji Synoptic Editora (jeszcze nie zbudowana).

## 4. Sesja porządkowa

- Usunięte strony Environment i Lighting (fasady bez podłączenia do
  `tag_manager`, jeden miał realny bug — niezdefiniowana zmienna).
- Naprawiony prawdziwy bug logowania PIN-em: `AccessManager` używał
  ścieżki względnej do pliku configu, więc różne katalogi startowe
  tworzyły różne pliki z różnymi PIN-ami — naprawione przez ścieżkę
  bezwzględną (ten sam problem naprawiony proaktywnie w
  `ProjectManager`/`ProtectionVerifier`).
- Naprawiony realny "fasadowy" przycisk: eksport CSV w Event Recorderze
  nic nie robił — podłączony naprawdę.

## 5. Device Status (Main View) — naprawa niespójności z żywymi danymi

Panel faktycznie nasłuchiwał prawdziwych tagów `Device.*.Status`, ale
tracił jednorazowe zdarzenie przejścia OFFLINE→ONLINE z powodu wyścigu
przy starcie (SimulatorDriver emitował je zanim GUI zdążyło podłączyć
most zdarzeń). Naprawione przez odczyt bieżącej wartości bezpośrednio przy
konstrukcji strony, nie tylko poleganie na przyszłym evencie — ten sam
wzorzec zastosowany później też przy wskaźniku sync czasu.

## 6. Weryfikacja generyczności DI/DO

Potwierdzone: domyślne opisy w pełni generyczne, persystencja opisów
kluczowana po nazwie tagu, zero logiki specyficznej dla jednego obiektu.
Jedyne ograniczenie: 4 z 64 kanałów DO miały wtedy zaszyte nazwy Q1/KMG/
KM1/KM2 — naprawione w kroku 12 poniżej.

## 7. Wskaźnik synchronizacji czasu

- `w32tm /query /status` (Windows Time service) zamiast bezpośredniego
  zapytania NTP przez `ntplib` — uzasadnienie: sieć przemysłowa zwykle
  bez dostępu do internetu, `ntplib` zawsze pokazywałby "brak sync",
  nawet gdyby lokalny serwer NTP/AD miał maszynę zsynchronizowaną.
- Wskaźnik w pasku statusu (zielony/czerwony/żółty), z tooltipem źródła.
- Hook pod GPS przygotowany (`report_gps_status()`), nieużywany — brak
  fizycznego GPS.

## 8. Niezależny dziennik audytowy

- Nowa tabela `audit_log` w bazie (migracja Alembic), osobna od
  `tag_history`/`alarm_history` operacyjnych.
- Rejestruje: logowania (w tym nieudane próby), zmiany PIN, zmiany
  nastaw Protection Settings, zmiany języka — kto, kiedy, wynik.
- Osobna strona nawigacyjna (nie zakładka w Events — świadoma decyzja,
  uzasadniona w ówczesnym raporcie), dostęp Engineer-only.

## 9. Menu Help → About

Nazwa, wersja (jedno źródło prawdy: `epw_os/version.py`, wcześniej
"v1.0.0" było tylko w pasku statusu), krótki opis.

## 10. Naprawa crasha przy zamykaniu (exit 139 / segfault)

Znaleziony i naprawiony realny, powtarzalny bug (reprodukowany lokalnie
z `-X faulthandler`, potwierdzony identyczny z symptomem zgłoszonym przez
CI): `MainWindow` rejestrował się jako event filter na globalnym
`QApplication` (do śledzenia aktywności użytkownika), ale nigdy nie
wyrejestrowywał się, jeśli okno nie przechodziło przez normalne
zamknięcie — zostawiony wiszący wskaźnik segfaultował przy zamykaniu
procesu. Naprawione przez nową, idempotentną `MainWindow.shutdown_gui()`,
wołaną z każdej ścieżki zamknięcia.

## 11. System Topology — naprawa fałszywych danych

Diagram i tabela informacyjna pokazywały **w 100% zahardkodowane** dane
(`"Status": "ONLINE"` na sztywno, zero połączenia z `tag_manager`) —
sprostowanie błędnego założenia z brief'u, że to źródło "żywych danych".
Naprawione: 4 węzły diagramu podłączone pod te same tagi `Device.*.Status`
co panel Device Status na Main View, z tym samym wzorcem "seeduj z
bieżącej wartości". Pozostałe zmyślone pola (CPU Load, Frames RX/TX,
Temperature...) świadomie NIE podłączone pod fałszywe-ale-wiarygodne
dane — zostawione jako czytelnie oznaczone placeholdery (żaden
odpowiadający tag nie istnieje nigdzie w systemie).

## 12. Uogólnienie Q1/KMG/KM1/KM2 (4 miejsca w kodzie)

Znalezione i naprawione dokładnie 4 miejsca z zaszytymi na sztywno
nazwami urządzeń specyficznych dla jednego projektu testowego:
`page_control_outputs.py` (klucz routingu komend), `epw_core.py`
(domyślne definicje komend), `page_entry_gate.py` (diagram synoptyczny —
etykieta I klucz routingu jednocześnie), `protection_verifier.py`
(komunikaty warunków bezpieczeństwa — **tylko etykieta**, sprawdzana
logika/tagi bezpieczeństwa bez zmian). Wszystko zamienione na generyczny
tag DO0N; prawdziwe nazwy urządzeń żyją teraz wyłącznie w edytowalnych
przez operatora opisach, spójnie między Control Outputs i Main View.

## 13. Kwitowanie alarmów

`AlarmManager` był już w pełni zaimplementowany (stan, trigger/ack/clear),
ale kompletnie niepodłączony do GUI. Zbudowane na nim: pole `ack_user`
(kto potwierdził), strona z listą alarmów, przycisk Acknowledge
(Operator+), wizualne odróżnienie niepotwierdzonych/potwierdzonych/
normalnych. Realne, obserwacyjne źródła alarmów: awaria komunikacji
urządzenia (COMM_FAILURE) i EMERGENCY_STOP — zero zgadywanej logiki
bezpieczeństwa.

## 14. Eksport CSV z Historiana (ogólny, trendy tagów)

Osobna funkcja od eksportu CSV w Event Recorderze (tamten eksportuje log
zdarzeń, to — surowe trendy wartości `tag_history`, dowolny tag, zakres
dat). Menu Tools → "Export Historical Data...". Znaleziony i naprawiony
realny bug: pickery dat pokazywały czas lokalny, baza przechowuje UTC —
bez konwersji eksport cichcem gubiłby dane (na testowej maszynie:
przesunięcie 2h).

## 15. Tryb wygaszania ekranu

Niezależny od auto-wylogowania (5 min) — osobny, konfigurowalny w
Settings czas bezczynności (domyślnie 2 min), budzi się na dowolny
dotyk/klik/klawisz. Czarny nakładający widget zakrywający całe okno
(łącznie z paskiem menu/statusu).

## 16. Analog Inputs → w pełni dynamiczny Menedżer Punktów

Najnowsza, największa zmiana architektoniczna tej serii. Digital Inputs/
Control Outputs **celowo pozostały bez zmian** (fizyczny limit zacisków
ELA/ADA — zweryfikowane wprost: 64 DI, 60 DO, żadnej zmiany).

- Stała lista 16 symulowanych kanałów (`ANALOG_CHANNEL_COUNT = 16`,
  zaszyta w trzech miejscach) zastąpiona dynamiczną kolekcją punktów w
  `project.json` (`analog_points`) — operator dodaje/usuwa punkty
  swobodnie, bez zmiany kodu.
- Każdy punkt: unikalny Tag/Adres (nadawany przez operatora, np.
  `AI.Garden.SoilMoisture`), Description, Signal type, zakresy
  surowy/inżynierski, jednostka, miejsca po przecinku, **Technical note**
  (nowe pole, czysto dokumentacyjne, np. "DHT11, magistrala 1-Wire,
  moduł ELA-02").
- Migracja istniejących 16 kanałów do nowego formatu — leniwa,
  jednorazowa, zachowuje wcześniejszą personalizację (zweryfikowana na
  spreparowanym "starym" `project.json`, i uruchomiona naprawdę na
  realnym pliku tego repozytorium).
- Przyciski "Add Point" / "Remove Point" (usuwanie z potwierdzeniem).
  Każdy punkt nadal rejestruje się jako prawdziwy Tag w `TagManager`
  (nowa zdolność: `TagManager.remove_tag()` — wcześniej tagi dało się
  tylko dodawać).
- Symulator (`SimulatorDriver`) sterowany teraz dynamiczną listą tagów,
  nie stałym zakresem — nowo dodany punkt dostaje żywe wartości w ciągu
  ok. 2 sekund od dodania (zweryfikowane empirycznie).

---

## Metodologia stosowana konsekwentnie w całej serii sesji

- **Weryfikacja empiryczna, nie tylko czytanie kodu** — każda naprawiona
  funkcja testowana przez realne uruchomienie `EPWCore`+`MainWindow`
  (offscreen), nie tylko przez logiczną analizę.
- **Zero zgadywania przy niejasnościach** — decyzje projektowe i
  ograniczenia opisywane wprost w raportach sesji jako "WYMAGA DECYZJI"
  zamiast domyślnego zgadywania.
- **`safety_kernel.py` i `interlock_engine.py` nietknięte** przez całą
  serię sesji, zgodnie ze stałym ograniczeniem.
- Każda sesja: osobna gałąź feature, małe logiczne commity, pełny zestaw
  testów (`pytest`, `test_headless.py`, `test_gui_smoke.py`) uruchamiany
  wielokrotnie (min. 3x) po każdej zmianie.
- Kilkukrotnie znaleziony i naprawiony ten sam wzorzec bugów: "seeduj z
  bieżącej wartości przy starcie, nie polegaj wyłącznie na przyszłym
  evencie" — bo tła symulacyjne/sprzętowe potrafią wyemitować
  jednorazowe zdarzenie zanim GUI zdąży się podłączyć.

## Stan repozytorium

- `main` zawiera: system dostępu, Control Outputs 64-kanałowy, MAIN VIEW,
  sesję porządkową, Device Status, weryfikację DI/DO, sync czasu, dziennik
  audytowy, Help/About, naprawę crasha, System Topology, genericję
  Q1/KMG/KM1/KM2, kwitowanie alarmów, eksport CSV, wygaszanie ekranu.
- `feature/analog-points-manager` (ta gałąź, jeszcze niezmergowana do
  `main`): Menedżer Punktów Analog Inputs — punkt 16 powyżej.
