// feat/help-system commit 3 - full content for chapters 1-4, Polish and
// English. Every claim here was checked against the actual code before
// being written (DeviceSchema.ts, DeviceValidation.ts, ProjectManager.ts,
// DeviceRegistryQueries.ts, ProjectV2Schema.ts) - see this task's own
// completion report for the discrepancies that surfaced along the way.

import type { HelpContentMap } from './HelpContentRegistry';

export const HELP_CONTENT_CORE: HelpContentMap = {
  // ==================== CHAPTER 1 - INTRODUCTION ====================
  'intro-what': {
    pl: [
      { kind: 'p', text: 'EPW-Synoptic-Editor tworzy i waliduje pliki projektu dla ekranu schematu elektrycznego/wodnego/wentylacyjnego: symbole, przewody, mierniki, panele sygnalizacyjne. To narzedzie EDYCYJNE - dziala offline, na pliku na dysku, i nie ma pojecia o zadnym zywym stanie instalacji.' },
      { kind: 'p', text: 'Edytor NIE wykonuje logiki sterowania, NIE odpytuje sterownikow po Modbusie ani zadnym innym protokole, i NIE wie, czy stycznik jest aktualnie zalaczony. Wszystko, co widac na ekranie podczas edycji - stan diody, wartosc na mierniku - to podglad ustawiony recznie w polu `Editor Preview`, nie odczyt z prawdziwego urzadzenia.' },
      { kind: 'p', text: 'Efektem pracy w tym edytorze jest plik projektu (rozszerzenie `.epwsyn`) zawierajacy geometrie ekranu i liste aparatow. Ten plik dopiero PRZEZNACZONY jest do uruchomienia w [[intro-platform|EPW-OS]] - zobacz rozdzial 10 po szczegoly, co dzis faktycznie dziala na tej sciezce.' },
      { kind: 'note', text: 'Zasada, ktora wraca w kazdym rozdziale tej pomocy: jesli czegos nie widac wprost w programie albo w pliku projektu, to tego nie ma. Ten tekst opisuje kod takim, jaki jest.' },
    ],
    en: [
      { kind: 'p', text: 'EPW-Synoptic-Editor creates and validates project files for an electrical/water/ventilation schematic screen: symbols, wires, meters, signal panels. It is an EDITING tool - it runs offline, against a file on disk, and has no notion of any live plant state.' },
      { kind: 'p', text: 'The editor does NOT execute control logic, does NOT poll controllers over Modbus or any other protocol, and does NOT know whether a contactor is currently energized. Everything shown on screen while editing - a lit diode, a value on a meter - is a preview set by hand in the `Editor Preview` field, not a reading from a real device.' },
      { kind: 'p', text: 'The output of working in this editor is a project file (`.epwsyn`) holding the screen geometry and the device list. That file is INTENDED to run on [[intro-platform|EPW-OS]] - see chapter 10 for exactly what that path actually does today.' },
      { kind: 'note', text: 'A rule that comes back in every chapter of this help: if something is not plainly visible in the program or in the project file, it does not exist. This text describes the code as it actually is.' },
    ],
  },
  'intro-platform': {
    pl: [
      { kind: 'p', text: 'Platforma EPW sklada sie z trzech osobnych aplikacji, kazda w swoim wlasnym repozytorium:' },
      { kind: 'list', items: [
        'EPW-OS - aplikacja uruchomieniowa. Wyswietla ekrany, odczytuje i zapisuje sygnaly na prawdziwym sprzecie, obsluguje alarmy, poziomy dostepu, historie.',
        'EPW-Logic-Studio - buduje automatyke: regoly sterowania, blokady, sekwencje. To tam definiuje sie np. prog ostrzegawczy licznika przelaczen (zobacz [[dev-switched|4.4]]).',
        'EPW-Synoptic-Editor (ten program) - tworzy grafike ekranu i liste aparatow, ktore EPW-OS potem wyswietla i EPW-Logic-Studio wykorzystuje w regulach.',
      ] },
      { kind: 'p', text: 'W dokumentacji EPW-OS (pliki `epw_os/gui/widgets/synoptic_runtime.py`, `epw_os/gui/main_window.py`) pojawia sie wzmianka o Home Assistant jako warstwie DODATKOWEJ - kazdy aparat SWITCHED/SIGNAL/MEASURED/MODULATED ma pole `publishToHa`, ktore mowi, czy jego stan ma trafic tez do Home Assistant jako encja. Home Assistant nie jest jednak torem sterowania: nic w tym edytorze ani w kontrakcie DeviceSchema nie zaklada, ze polecenie moze przyjsc STAMTAD z powrotem do sterownika - to wygoda podgladu/powiadomien, nie kanal komend.' },
      { kind: 'note', text: 'Rozbieznosc znaleziona podczas pisania tej pomocy: EPW-Logic-Studio, wymienione w tresci tego zadania jako aplikacja majaca juz wlasny system pomocy w stylu Windows 98, w rzeczywistosci go NIE MA (sprawdzone w kodzie repozytorium) - tylko EPW-OS go posiada. Ten fakt zglaszany jest w raporcie ukonczenia zadania.' },
    ],
    en: [
      { kind: 'p', text: 'The EPW platform is three separate applications, each in its own repository:' },
      { kind: 'list', items: [
        'EPW-OS - the runtime application. Displays screens, reads and writes signals on real hardware, handles alarms, access levels, history.',
        'EPW-Logic-Studio - builds automation: control rules, interlocks, sequences. That is where, for example, the switch-counter warning threshold is defined (see [[dev-switched|4.4]]).',
        'EPW-Synoptic-Editor (this program) - builds the screen graphics and the device list that EPW-OS then displays and EPW-Logic-Studio consumes in its rules.',
      ] },
      { kind: 'p', text: 'EPW-OS\'s own code (`epw_os/gui/widgets/synoptic_runtime.py`, `epw_os/gui/main_window.py`) mentions Home Assistant as an ADDITIONAL layer - every SWITCHED/SIGNAL/MEASURED/MODULATED device has a `publishToHa` field saying whether its state should also reach Home Assistant as an entity. Home Assistant is not a control path, though: nothing in this editor or in the DeviceSchema contract assumes a command can come back FROM there to a controller - it is a convenience for monitoring/notifications, not a command channel.' },
      { kind: 'note', text: 'A discrepancy found while writing this help: EPW-Logic-Studio, named in this task\'s own brief as already having a Windows-98-style help system, does NOT actually have one (checked directly in its repository) - only EPW-OS does. Reported in this task\'s own completion report.' },
    ],
  },
  'intro-principle': {
    pl: [
      { kind: 'p', text: 'Cala architektura tej platformy trzyma sie jednej zasady: EKRAN INFORMUJE, SPRZET CHRONI. Synoptyka i logika w EPW-Logic-Studio pokazuja operatorowi stan i dostarczaja wygodne, kontekstowe blokady - ale ostateczna ochrona (bezpiecznik, stycznik z wlasna cewka zanikowa, zawor zwrotny) musi istniec fizycznie, niezaleznie od tego, co dzieje sie na ekranie.' },
      { kind: 'p', text: 'W tym edytorze zasada ta widac wprost w kontrakcie aparatu SWITCHED: pole `safeState` (patrz [[dev-switched|4.4]]) opisuje, co aparat ma zrobic PRZY STARCIE i PRZY UTRACIE LACZNOSCI - a nie co ma zrobic operator recznie w takiej sytuacji. To sprzet i jego wlasna konfiguracja decyduja o stanie bezpiecznym, nie logika ekranu.' },
      { kind: 'p', text: 'Podobnie: brak wejscia zwrotnego (`feedback.mode` NONE, patrz [[dev-switched|4.4]]) oznacza, ze ekran nigdy nie potwierdzi, czy polecenie faktycznie zadzialalo. To swiadomy, dopuszczony wybor konfiguracji - ale konsekwencja jest wprost nazwana w formularzu aparatu, nie ukryta.' },
    ],
    en: [
      { kind: 'p', text: 'The whole platform architecture holds to one rule: THE SCREEN INFORMS, THE HARDWARE PROTECTS. The synoptic and EPW-Logic-Studio\'s own logic show the operator state and provide convenient, contextual interlocks - but the final protection (a fuse, a contactor with its own undervoltage coil, a check valve) has to exist physically, independent of whatever the screen is doing.' },
      { kind: 'p', text: 'In this editor the rule shows up directly in the SWITCHED device contract: the `safeState` field (see [[dev-switched|4.4]]) describes what the device itself should do ON STARTUP and ON LINK LOSS - not what an operator should do by hand in that situation. The hardware and its own configuration decide the safe state, not the screen\'s logic.' },
      { kind: 'p', text: 'Likewise: no feedback (`feedback.mode` NONE, see [[dev-switched|4.4]]) means the screen will never confirm whether a command actually took effect. That is a deliberate, allowed configuration choice - but its consequence is named outright in the device form, not hidden.' },
    ],
  },
  'intro-screens': {
    pl: [
      { kind: 'p', text: 'Kazdy projekt to ekran SCHEMATIC: symbole, przewody, mierniki, panele sygnalizacyjne (rozdzial [[sch-node-model|5]]). Zapisywany jest w pliku jako pole `kind`, ale SCHEMATIC to dzis jedyna wartosc, jaka to pole moze mieć w NOWO zapisanym pliku.' },
      { kind: 'p', text: 'Wczesniejsza wersja tego edytora miala tez drugi rodzaj ekranu, PLAN (rzut izometryczny dzialki, wlasna kanwa, wlasna biblioteka obiektow na kaflach) - zostal on calkowicie usuniety. Pole `kind` zostalo w formacie pliku wylacznie po to, zeby STARY plik zapisany z `kind: "PLAN"` wciaz dalo sie otworzyc: taki plik wczytuje sie normalnie, jego ekran jest cicho konwertowany na SCHEMATIC, a w panelu Messages pojawia sie o tym informacja - plik NIE jest odrzucany, a numer wersji schematu (`schema_version`) sie nie zmienia.' },
      { kind: 'p', text: 'Plik bez pola `kind` w ogole (kazdy plik zapisany, zanim ten koncept powstal) wczytuje sie jako SCHEMATIC bez zadnego komunikatu - to byl, i nadal jest, jedyny sensowny domyslny rodzaj ekranu.' },
    ],
    en: [
      { kind: 'p', text: 'Every project is a SCHEMATIC screen: symbols, wires, meters, signal panels (chapter [[sch-node-model|5]]). It is saved in the file as the `kind` field, but SCHEMATIC is now the only value that field can have in a NEWLY saved file.' },
      { kind: 'p', text: 'An earlier version of this editor also had a second screen kind, PLAN (an isometric plot plan, with its own canvas and its own library of tile-based objects) - it has been removed entirely. The `kind` field stays in the file format only so an OLDER file saved with `kind: "PLAN"` still opens: such a file loads normally, its screen is silently converted to SCHEMATIC, and a notice about that appears in the Messages panel - the file is NOT rejected, and the schema version number (`schema_version`) does not change.' },
      { kind: 'p', text: 'A file with no `kind` field at all (every file saved before this concept existed) loads as SCHEMATIC with no message at all - that was, and still is, the only sensible default screen kind.' },
    ],
  },

  // ==================== CHAPTER 2 - GETTING STARTED ====================
  'start-new-project': {
    pl: [
      { kind: 'p', text: 'Menu `File > New` tworzy pusty projekt SCHEMATIC (prosi o nazwe). Zaczyna od zera: bez lokalizacji, kart, aparatow ani obiektow - te trzeba dodac recznie, w kolejnosci opisanej w [[start-order|2.2]].' },
      { kind: 'p', text: 'Jesli w otwartym projekcie sa niezapisane zmiany, `New`/`Open...` pytaja o potwierdzenie przed ich utrata (standardowe okno przegladarki, nie da sie go dostosowac tresciowo).' },
    ],
    en: [
      { kind: 'p', text: '`File > New` creates an empty SCHEMATIC project (asks for a name). It starts from nothing: no locations, cards, devices or objects - those must be added by hand, in the order described in [[start-order|2.2]].' },
      { kind: 'p', text: 'If the open project has unsaved changes, `New`/`Open...` ask for confirmation before discarding them (the browser\'s own standard dialog - its wording cannot be customized).' },
    ],
  },
  'start-order': {
    pl: [
      { kind: 'p', text: 'Praktyczna kolejnosc pracy nad nowym projektem SCHEMATIC to: NAJPIERW rejestry (lokalizacje i karty, rozdzial 3), POTEM aparaty (rozdzial 4), a DOPIERO POTEM symbole na ekranie (rozdzial 6).' },
      { kind: 'p', text: 'Powod jest wprost w kontrakcie danych: identyfikator aparatu MUSI zaczynac sie kodem juz istniejacej lokalizacji (`validateDeviceId` w `DeviceValidation.ts`), a kazdy adres kanalu MUSI wskazywac na juz istniejaca karte (`validateChannelAddress`). Formularz aparatu wymusza to bezposrednio: przy tworzeniu nowego aparatu pole Id to rozwijana lista lokalizacji, nie wolny tekst - jesli lista jest pusta, dodanie aparatu jest zablokowane z podpowiedzia "Najpierw dodaj lokalizacje w Rejestrach projektu".' },
      { kind: 'p', text: 'Symbol na ekranie schematu nie tworzy aparatu - tylko wskazuje na juz istniejacy przez rozwijana liste Aparat we Properties ([[sym-device-binding|6.4]]). Umieszczenie symbolu przed dodaniem aparatow po prostu zostawia go bez przypisania (co jest poprawnym stanem - patrz [[dev-why-not-in-screen|4.1]]) do czasu, az aparat powstanie.' },
    ],
    en: [
      { kind: 'p', text: 'The practical order for a new SCHEMATIC project is: registries FIRST (locations and cards, chapter 3), THEN devices (chapter 4), and ONLY THEN symbols on the screen (chapter 6).' },
      { kind: 'p', text: 'The reason is right in the data contract: a device id MUST start with an already-existing location\'s code (`validateDeviceId` in `DeviceValidation.ts`), and every channel address MUST point at an already-existing card (`validateChannelAddress`). The device form enforces this directly: when creating a new device, the Id field is a dropdown of locations, not free text - if that list is empty, adding a device is blocked with a hint to add a location in Project Registries first.' },
      { kind: 'p', text: 'A symbol on the schematic screen does not create a device - it only points at one that already exists, through the Aparat dropdown in Properties ([[sym-device-binding|6.4]]). Placing a symbol before any devices exist simply leaves it unassigned (a valid state - see [[dev-why-not-in-screen|4.1]]) until a device is created for it to point at.' },
    ],
  },
  'start-save-open': {
    pl: [
      { kind: 'p', text: '`File > Save` i `Save As...` zapisuja caly stan projektu do jednego pliku `.epwsyn` (format JSON, pole `format: "EPW_SYNOPTIC"`) przez natywny mechanizm zapisu pliku przegladarki. `File > Open...` czyta taki plik z powrotem.' },
      { kind: 'p', text: 'Zapisywane jest wszystko: metadane projektu, konfiguracja kanwy, obiekty i przewody, mierniki i panele sygnalizacyjne, ramki, lokalizacje/karty/aparaty, rodzaj ekranu oraz wybrany jezyk pomocy. Szczegoly zawartosci pliku sa w [[file-contents|10.1]].' },
      { kind: 'p', text: 'Wczytanie pliku ze zbyt nowa wersja schematu (pole `schema_version` wieksze niz obslugiwana) jest odrzucane z komunikatem bledu zamiast czesciowego, nieprzewidywalnego wczytania - zobacz [[file-versioning|10.2]].' },
    ],
    en: [
      { kind: 'p', text: '`File > Save` and `Save As...` write the whole project state to one `.epwsyn` file (JSON, `format: "EPW_SYNOPTIC"`) through the browser\'s own native file-save mechanism. `File > Open...` reads such a file back.' },
      { kind: 'p', text: 'Everything is saved: project metadata, canvas configuration, objects and wires, meters and signal panels, frames, locations/cards/devices, the screen kind, and the chosen help language. Full file contents are covered in [[file-contents|10.1]].' },
      { kind: 'p', text: 'Loading a file with a schema version newer than what this build supports (`schema_version` field) is rejected with an error rather than a partial, unpredictable load - see [[file-versioning|10.2]].' },
    ],
  },
  'start-example': {
    pl: [
      { kind: 'p', text: 'Kompletny przyklad: obwod od przylacza (punkt graniczny) przez szyne zbiorcza do dwoch odbiorow (dwoch stycznikow sterujacych oswietleniem). Krok po kroku, z konkretnymi wartosciami.' },
      { kind: 'heading', text: 'Krok 1 - rejestry' },
      { kind: 'list', ordered: true, items: [
        'Menu Aparaty > Rejestry projektu... > zakladka Lokalizacje: dodaj kod `MAG` (opis "Magazyn").',
        'Zakladka Karty: dodaj karte `ELA1` (model dowolny, rodzaj DI, 16 kanalow) i karte `ADA1` (rodzaj DO, 16 kanalow).',
      ] },
      { kind: 'heading', text: 'Krok 2 - dwa aparaty SWITCHED' },
      { kind: 'list', ordered: true, items: [
        'Menu Aparaty > Lista aparatow... > + Dodaj. Id: lokalizacja `MAG`, sufiks `OSW1`. Oznaczenie `-K1`, nazwa "Oswietlenie regalu 1". Zachowanie SWITCHED, tryb sprzezenia DUAL, diClosed `ELA1.DI.1`, diOpen `ELA1.DI.2`. Sterowanie: 1 wyjscie, styl MAINTAINED, doClose `ADA1.DO.1`. Zapisz.',
        'Powtorz dla drugiego odbioru: sufiks `OSW2`, oznaczenie `-K2`, diClosed `ELA1.DI.3`, diOpen `ELA1.DI.4`, doClose `ADA1.DO.2`.',
      ] },
      { kind: 'heading', text: 'Krok 3 - ekran schematu' },
      { kind: 'list', ordered: true, items: [
        'Przeciagnij z biblioteki symbol Boundary Point na plotno. We Properties ustaw Boundary Direction na SOURCE i Boundary Medium na ELECTRICAL.',
        'Wybierz osrodek 1 (Electrical, klawisz `1`) i narysuj przewod ze stycznikiem punktu granicznego do miejsca, gdzie zacznie sie szyna.',
        'Ustaw styl NOWEGO przewodu na Bus (przelacznik w gornym pasku narzedzi) i narysuj krotki, poziomy odcinek szyny.',
        'Przeciagnij dwa symbole Circuit Breaker (albo Disconnect Switch) w poblize szyny. Narysuj po jednym przewodzie od kazdego z nich, konczac DOKLADNIE na dowolnym punkcie dlugosci szyny (nie tylko na jej koncu) - patrz [[sch-wire-style|5.4]].',
        'Zaznacz kazdy z dwoch symboli i we Properties, w polu Aparat, wybierz odpowiednio `MAG_OSW1` i `MAG_OSW2`.',
      ] },
      { kind: 'p', text: 'Efekt: obie galezie licza sie do JEDNEJ sieci elektrycznej (bo stykaja sie geometrycznie z ta sama szyna - patrz [[sch-node-model|5.1]]), a kazdy symbol pokazuje oznaczenie swojego aparatu (bo zostalo wypelnione automatycznie przy przypisaniu, patrz [[sym-device-binding|6.4]]).' },
    ],
    en: [
      { kind: 'p', text: 'A complete example: a circuit from a supply point (a boundary point) through a busbar to two loads (two contactors controlling lighting). Step by step, with concrete values.' },
      { kind: 'heading', text: 'Step 1 - registries' },
      { kind: 'list', ordered: true, items: [
        'Menu Aparaty > Rejestry projektu... > Lokalizacje tab: add code `MAG` (description "Warehouse").',
        'Karty tab: add card `ELA1` (any model, kind DI, 16 channels) and card `ADA1` (kind DO, 16 channels).',
      ] },
      { kind: 'heading', text: 'Step 2 - two SWITCHED devices' },
      { kind: 'list', ordered: true, items: [
        'Menu Aparaty > Lista aparatow... > + Dodaj. Id: location `MAG`, suffix `OSW1`. Designation `-K1`, name "Shelf lighting 1". Behavior SWITCHED, feedback mode DUAL, diClosed `ELA1.DI.1`, diOpen `ELA1.DI.2`. Command: 1 output, style MAINTAINED, doClose `ADA1.DO.1`. Save.',
        'Repeat for the second load: suffix `OSW2`, designation `-K2`, diClosed `ELA1.DI.3`, diOpen `ELA1.DI.4`, doClose `ADA1.DO.2`.',
      ] },
      { kind: 'heading', text: 'Step 3 - the schematic screen' },
      { kind: 'list', ordered: true, items: [
        'Drag a Boundary Point symbol from the library onto the canvas. In Properties, set Boundary Direction to SOURCE and Boundary Medium to ELECTRICAL.',
        'Select medium 1 (Electrical, key `1`) and draw a wire from the boundary point\'s terminal to where the busbar will start.',
        'Set the NEW wire\'s style to Bus (the toggle in the top toolbar) and draw a short, horizontal busbar segment.',
        'Drag two Circuit Breaker (or Disconnect Switch) symbols near the busbar. Draw one wire from each, ending EXACTLY on any point along the busbar\'s length (not only at its end) - see [[sch-wire-style|5.4]].',
        'Select each of the two symbols and, in Properties, in the Aparat field, choose `MAG_OSW1` and `MAG_OSW2` respectively.',
      ] },
      { kind: 'p', text: 'Result: both branches count as ONE electrical net (because they touch the same busbar geometrically - see [[sch-node-model|5.1]]), and each symbol shows its own device\'s designation (auto-filled the moment it was assigned - see [[sym-device-binding|6.4]]).' },
    ],
  },

  // ==================== CHAPTER 3 - PROJECT REGISTRIES ====================
  'reg-locations': {
    pl: [
      { kind: 'p', text: 'Lokalizacja to KROTKI PRZEDROSTEK identyfikatora aparatu, nie jego nazwa. Przyklady poprawnych kodow: `KOT` (kotlownia), `BRAMA`, `MAG` (magazyn), `OGROD`. Kod musi skladac sie wylacznie z wielkich liter A-Z i cyfr 0-9 (regula `LOCATION_INVALID_CODE` w `DeviceValidation.ts`) - male litery sa odrzucane.' },
      { kind: 'p', text: 'Lokalizacja aparatu jest WYLICZANA z przedrostka jego identyfikatora (czesc przed pierwszym podkresleniem), a NIE przechowywana jako osobne pole na aparacie. Z tego wynika konkretna, praktyczna konsekwencja: przeniesienie aparatu do innej lokalizacji nie jest "edycja" - identyfikator jest niezmienny po utworzeniu ([[dev-naming|4.2]]), wiec jedynym sposobem jest USUNIECIE aparatu i UTWORZENIE go od nowa pod nowym identyfikatorem, z tymi samymi wartosciami pol.' },
      { kind: 'p', text: 'Rejestr lokalizacji otwiera sie z menu Aparaty > Rejestry projektu..., zakladka Lokalizacje. Dodawanie wymaga kodu i opisu; edycja pozwala zmienic tylko opis - kod, raz nadany, jest tak samo niezmienny jak identyfikator aparatu, z tego samego powodu (jest juz czescia identyfikatorow istniejacych aparatow).' },
    ],
    en: [
      { kind: 'p', text: 'A location is a SHORT PREFIX for a device id, not a device name. Examples of valid codes: `KOT` (boiler room), `BRAMA` (gate), `MAG` (warehouse), `OGROD` (garden). The code must be uppercase letters A-Z and digits 0-9 only (the `LOCATION_INVALID_CODE` rule in `DeviceValidation.ts`) - lowercase letters are rejected.' },
      { kind: 'p', text: 'A device\'s location is DERIVED from the prefix of its id (the part before the first underscore), NOT stored as a separate field on the device. This has a concrete, practical consequence: moving a device to a different location is not an "edit" - the id is immutable once created ([[dev-naming|4.2]]), so the only way is to DELETE the device and CREATE it again under the new id, with the same field values.' },
      { kind: 'p', text: 'The location registry opens from the Aparaty menu > Rejestry projektu..., Lokalizacje tab. Adding one needs a code and a description; editing only lets you change the description - the code, once given, is just as immutable as a device id, for the same reason (it is already part of existing device ids).' },
    ],
  },
  'reg-cards': {
    pl: [
      { kind: 'p', text: 'Karta reprezentuje fizyczna karte wejsc/wyjsc sterownika: identyfikator (np. `ELA1`), model (etykieta opisowa, dowolny tekst), rodzaj kanalow (DI, DO, AI albo AO - jedna karta ma jeden rodzaj) i liczbe kanalow. Kanaly numerowane sa od 1.' },
      { kind: 'p', text: 'Rejestr kart daje dwie rzeczy: (1) walidacje kazdego adresu kanalu w formularzu aparatu - czy karta istnieje, czy jej rodzaj zgadza sie z rodzajem uzytym w adresie, czy numer kanalu miesci sie w zakresie 1..liczba_kanalow (`validateChannelAddress`); (2) wykrywanie podwojnego przypisania tego samego kanalu do dwoch roznych aparatow (`CHANNEL_ADDRESS_COLLISION`) - pikcer kanalu w formularzu aparatu od razu wyszarza kazdy kanal juz zajety, pokazujac przez kogo.' },
      { kind: 'p', text: 'Bez zadnej karty w rejestrze nie da sie wpisac zadnego poprawnego adresu kanalu - kazdy picker kanalu w formularzu aparatu filtruje karty po rodzaju wymaganym dla danego pola (np. picker `input` aparatu MEASURED pokazuje tylko karty AI).' },
    ],
    en: [
      { kind: 'p', text: 'A card represents a physical I/O card on the controller: an id (e.g. `ELA1`), a model (a free-text description label), a channel kind (DI, DO, AI or AO - one card has exactly one kind) and a channel count. Channels are numbered starting from 1.' },
      { kind: 'p', text: 'The card registry gives two things: (1) validating every channel address in the device form - does the card exist, does its kind match the kind used in the address, is the channel number within 1..channel_count (`validateChannelAddress`); (2) detecting the same channel assigned to two different devices at once (`CHANNEL_ADDRESS_COLLISION`) - the channel picker in the device form immediately greys out any channel already taken, showing by whom.' },
      { kind: 'p', text: 'With no card in the registry at all, no valid channel address can be entered anywhere - every channel picker in the device form filters cards by the kind that field actually requires (e.g. a MEASURED device\'s `input` picker only ever shows AI cards).' },
    ],
  },
  'reg-addressing': {
    pl: [
      { kind: 'p', text: 'Format adresu kanalu to `KARTA.RODZAJ.KANAL`, na przyklad `ELA1.DI.12` albo `ADA1.DO.4`. Rodzaj to jeden z DI (wejscie cyfrowe), DO (wyjscie cyfrowe), AI (wejscie analogowe), AO (wyjscie analogowe). Numeracja kanalow zaczyna sie od 1, nie od 0.' },
      { kind: 'p', text: 'Biale znaki wokol calego adresu lub wokol kazdej z trzech czesci sa ignorowane przy porownywaniu - `ELA1.DI.12` i ` ELA1 . DI . 12 ` to ten sam adres dla wykrywania kolizji. Wiodace zera tez nie maja znaczenia: `ELA1.DI.12` i `ELA1.DI.012` rowniez licza sie jako ten sam, jeden fizyczny kanal.' },
      { kind: 'p', text: 'W samym formularzu aparatu adres nigdy nie jest wpisywany recznie jako tekst - picker kanalu ([[dev-form-validation|4.8]]) to trzy powiazane pola (karta, wtedy dostepny rodzaj wynika z karty, wtedy numer kanalu z listy 1..liczba_kanalow tej karty), wiec zly format jest praktycznie niemozliwy do wprowadzenia przez interfejs. Sam tekstowy format ma znaczenie przy odczytywaniu pliku projektu recznie albo z zewnetrznego zrodla.' },
    ],
    en: [
      { kind: 'p', text: 'A channel address has the format `CARD.KIND.CHANNEL`, for example `ELA1.DI.12` or `ADA1.DO.4`. Kind is one of DI (digital input), DO (digital output), AI (analog input), AO (analog output). Channel numbering starts at 1, not 0.' },
      { kind: 'p', text: 'Whitespace around the whole address or around any of its three parts is ignored when comparing - `ELA1.DI.12` and ` ELA1 . DI . 12 ` are the same address for collision detection. Leading zeros do not matter either: `ELA1.DI.12` and `ELA1.DI.012` also count as the same single physical channel.' },
      { kind: 'p', text: 'Inside the device form itself, an address is never typed by hand as text - the channel picker ([[dev-form-validation|4.8]]) is three linked fields (a card, then the kind that follows from that card, then a channel number from that card\'s own 1..channel_count list), so a malformed format is practically impossible to enter through the interface. The plain text format matters when reading the project file by hand or from an external source.' },
    ],
  },
  'reg-delete-protection': {
    pl: [
      { kind: 'p', text: 'Usuniecie lokalizacji, ktorej kod jest przedrostkiem identyfikatora choc jednego istniejacego aparatu, jest zablokowane - przycisk Usun jest wygaszony, a najechanie na niego pokazuje liczbe aparatow, ktore go uzywaja.' },
      { kind: 'p', text: 'Podobnie usuniecie karty, ktorej choc jeden kanal jest wpisany w adres jakiegokolwiek aparatu, jest zablokowane - z tego samego powodu: usuniecie karty zostawiloby te aparaty z adresami wskazujacymi na nieistniejaca karte.' },
      { kind: 'p', text: 'To nie jest ograniczenie interfejsu dodane "na wszelki wypadek" - to bezposrednia konsekwencja tego, jak identyfikator aparatu i adres kanalu sa zbudowane (patrz [[reg-locations|3.1]] i [[reg-addressing|3.3]]): usuniecie uzywanej lokalizacji lub karty zostawiloby dane w stanie, ktorego `validateDeviceRegistry` nie potrafiloby juz uznac za poprawny.' },
    ],
    en: [
      { kind: 'p', text: 'Deleting a location whose code is the prefix of even one existing device\'s id is blocked - its Delete button is disabled, and hovering it shows how many devices use it.' },
      { kind: 'p', text: 'Likewise, deleting a card with even one channel referenced by any device\'s address is blocked - for the same reason: deleting the card would leave those devices with addresses pointing at a card that no longer exists.' },
      { kind: 'p', text: 'This is not an interface restriction added "just in case" - it is a direct consequence of how a device id and a channel address are built (see [[reg-locations|3.1]] and [[reg-addressing|3.3]]): deleting a location or card still in use would leave the data in a state `validateDeviceRegistry` could no longer call valid.' },
    ],
  },

  // ==================== CHAPTER 4 - DEVICE LIST ====================
  'dev-why-not-in-screen': {
    pl: [
      { kind: 'p', text: 'W tym edytorze aparat jest zdefiniowany RAZ, we wspolnej liscie projektu (Aparaty > Lista aparatow...). Element ekranu (symbol na schemacie, wiersz miernika, wiersz panelu sygnalizacyjnego) nigdy nie przechowuje konfiguracji aparatu - mowi tylko "w tym miejscu, tym symbolem, pokaz aparat KOT_KMG1", przez pole przechowujace jego identyfikator.' },
      { kind: 'p', text: 'Ten sam aparat pokazany na wielu symbolach albo nawet na wielu ekranach jest CELEM tej architektury, a nie bledem do wykrycia. Zaznaczenie dwoch roznych symboli wskazujacych na ten sam identyfikator aparatu nie zglasza zadnego bledu ([[sym-device-binding|6.4]]) - to normalny, poprawny stan.' },
      { kind: 'p', text: 'Wewnetrznie: `SynopticObject.deviceId` (symbol), `MeterElementRow.device` (wiersz miernika) i odpowiadajace pole wiersza panelu sygnalizacyjnego to zawsze BAJTY IDENTYFIKATORA, nigdy kopia pol aparatu. Jednostka i format miernika ([[elem-meter|7.1]]) sa zawsze czytane z aparatu w momencie wyswietlania, nigdy nie kopiowane na wiersz - zmiana jednostki na aparacie natychmiast zmienia to, co pokazuje kazdy wiersz, ktory na niego wskazuje.' },
    ],
    en: [
      { kind: 'p', text: 'In this editor a device is defined ONCE, in the project\'s shared list (Aparaty > Lista aparatow...). A screen element (a schematic symbol, a meter row, a signal panel row) never stores the device\'s configuration - it only says "at this spot, with this symbol, show device KOT_KMG1", through a field holding its id.' },
      { kind: 'p', text: 'The same device shown on many symbols, or even on many screens, is the GOAL of this architecture, not a bug to catch. Selecting two different symbols that point at the same device id reports no error at all ([[sym-device-binding|6.4]]) - that is a normal, valid state.' },
      { kind: 'p', text: 'Internally: `SynopticObject.deviceId` (a symbol), `MeterElementRow.device` (a meter row) and the matching field on a signal panel row are always just an ID STRING, never a copy of the device\'s own fields. A meter\'s unit and format ([[elem-meter|7.1]]) are always read from the device at display time, never copied onto the row - changing the unit on the device instantly changes what every row pointing at it shows.' },
    ],
  },
  'dev-naming': {
    pl: [
      { kind: 'p', text: 'Kazdy aparat ma trzy oddzielne pola tekstowe, kazde z inna rola:' },
      { kind: 'table', headers: ['Pole', 'Rola', 'Przyklad'], rows: [
        ['id', 'Klucz maszynowy, NIEZMIENNY po utworzeniu', '`KOT_KMG1`'],
        ['designation (oznaczenie)', 'To, co widac na schemacie', '`-K1`'],
        ['name (nazwa)', 'Opis dla czlowieka', '"Stycznik grzalki"'],
      ] },
      { kind: 'p', text: 'Zasada jest prosta: CZLOWIEK widzi oznaczenie (na symbolu, w tabelach), MASZYNA widzi id (adresy, odwolania z ekranu). Id musi skladac sie z wielkich liter, cyfr i dokladnie jednego podkreslenia, gdzie czesc przed podkresleniem jest kodem zarejestrowanej lokalizacji (`validateDeviceId`) - std. `KOT_KMG1` znaczy "aparat KMG1 w lokalizacji KOT".' },
      { kind: 'p', text: 'Id jest niezmienny, bo jest kluczem: element ekranu wskazuje na aparat WLASNIE po id ([[dev-why-not-in-screen|4.1]]), a lokalizacja aparatu jest z niego wyliczana ([[reg-locations|3.1]]). Formularz aparatu wprost blokuje edycje pola Id, gdy edytujemy juz istniejacy aparat - jest ono aktywne tylko przy tworzeniu nowego.' },
      { kind: 'p', text: 'Duplikowanie aparatu (przycisk Duplikuj w liscie) czysci WYLACZNIE id i oznaczenie w nowym szkicu - nazwa, rodzaj, zachowanie i cala konfiguracja szczegolowa (np. adresy kanalow) sa przepisywane bez zmian, wiec trzeba je swiadomie poprawic (przynajmniej adresy kanalow, ktore inaczej koliduja z oryginalem).' },
    ],
    en: [
      { kind: 'p', text: 'Every device has three separate text fields, each with a different role:' },
      { kind: 'table', headers: ['Field', 'Role', 'Example'], rows: [
        ['id', 'The machine key, IMMUTABLE once created', '`KOT_KMG1`'],
        ['designation', 'What is shown on the diagram', '`-K1`'],
        ['name', 'A human-readable description', '"Boiler heater contactor"'],
      ] },
      { kind: 'p', text: 'The rule is simple: A HUMAN sees the designation (on the symbol, in tables), THE MACHINE sees the id (addresses, screen references). The id must be uppercase letters, digits and exactly one underscore, where the part before the underscore is a registered location\'s code (`validateDeviceId`) - so `KOT_KMG1` reads as "device KMG1 in location KOT".' },
      { kind: 'p', text: 'The id is immutable because it is a key: a screen element points at a device BY its id ([[dev-why-not-in-screen|4.1]]), and a device\'s location is derived from it ([[reg-locations|3.1]]). The device form directly disables editing the Id field once an existing device is being edited - it is only active when creating a new one.' },
      { kind: 'p', text: 'Duplicating a device (the Duplikuj button in the list) clears ONLY the id and the designation in the new draft - the name, behavior and every detailed field (e.g. channel addresses) are carried over unchanged, so they must be deliberately corrected (at minimum the channel addresses, which would otherwise collide with the original).' },
    ],
  },
  'dev-behavior-classification': {
    pl: [
      { kind: 'p', text: 'Aparat jest klasyfikowany po ZACHOWANIU, a nie po rodzaju urzadzenia. Pole `kind` (np. "contactor", "valve", "sensor") to WYLACZNIE etykieta opisowa bez znaczenia funkcjonalnego - nie wplywa na zadna regule walidacji ani na to, jakie pola aparat ma. O tym, jakie pola, sygnaly i komendy ma aparat, decyduje wylacznie pole `behavior`.' },
      { kind: 'p', text: 'Sa dokladnie cztery zachowania, i nic wiecej nie moze byc po cichu dodane: SWITCHED ([[dev-switched|4.4]]), SIGNAL ([[dev-signal|4.5]]), MEASURED ([[dev-measured|4.6]]), MODULATED ([[dev-modulated|4.7]]). Wybor zachowania w formularzu zmienia caly dolny formularz - a jesli aparat mial juz wypelnione pola szczegolowe innego zachowania, zmiana pyta o potwierdzenie, bo je wyczysci.' },
    ],
    en: [
      { kind: 'p', text: 'A device is classified by BEHAVIOR, not by device kind. The `kind` field (e.g. "contactor", "valve", "sensor") is ONLY a descriptive label with no functional meaning - it affects no validation rule and none of the device\'s fields. What fields, signals and commands a device has is decided entirely by the `behavior` field.' },
      { kind: 'p', text: 'There are exactly four behaviors, and nothing else may be silently added: SWITCHED ([[dev-switched|4.4]]), SIGNAL ([[dev-signal|4.5]]), MEASURED ([[dev-measured|4.6]]), MODULATED ([[dev-modulated|4.7]]). Choosing a behavior in the form changes the whole lower section of it - and if the device already had detail fields filled in for a different behavior, changing it asks for confirmation, because it will clear them.' },
    ],
  },
  'dev-switched': {
    pl: [
      { kind: 'p', text: 'SWITCHED to sterowalne urzadzenie dwustanowe: stycznik, zawor, przepustnica. Ma wejscie zwrotne (feedback), wyjscie sterujace (command), nadzor (supervision) i stan bezpieczny (safeState).' },
      { kind: 'heading', text: 'Sprzezenie zwrotne (feedback.mode)' },
      { kind: 'p', text: 'Tryb DUAL uzywa dwoch wejsc cyfrowych (diClosed i diOpen), co pozwala odroznic cztery stany:' },
      { kind: 'table', headers: ['diClosed', 'diOpen', 'Znaczenie'], rows: [
        ['0', '1', 'Otwarty'],
        ['1', '0', 'Zamkniety'],
        ['0', '0', 'W ruchu albo przewod zerwany'],
        ['1', '1', 'Blad (oba krancowki jednoczesnie)'],
      ] },
      { kind: 'p', text: 'Tryb SINGLE uzywa jednego wejscia (diClosed) z opcjonalnym zanegowaniem (invert) i NIE ODROZNIA stanu posredniego ani zaniku sygnalu od stanu OFF - jest to swiadome ograniczenie tego trybu, nie usterka. Tryb NONE nie ma zadnego wejscia zwrotnego: sterowanie dziala w petli otwartej, ekran nigdy nie potwierdzi rzeczywistego stanu aparatu.' },
      { kind: 'heading', text: 'Sterowanie (command)' },
      { kind: 'p', text: 'Liczba wyjsc (1 albo 2) i styl (MAINTAINED albo PULSE) razem daja cztery ukladajace sie kombinacje:' },
      { kind: 'list', items: [
        '1 wyjscie, MAINTAINED - typowy stycznik/zawor z jedna cewka trzymana pod napieciem w stanie zalaczonym.',
        '1 wyjscie, PULSE - typowy przekaznik bistabilny sterowany krotkim impulsem.',
        '2 wyjscia, MAINTAINED - typowy zawor trojpolozeniowy z oddzielnymi cewkami OTWORZ/ZAMKNIJ.',
        '2 wyjscia, PULSE - typowy stycznik bistabilny z oddzielnymi impulsami ZALACZ/WYLACZ.',
      ] },
      { kind: 'p', text: 'Przy 2 wyjsciach pole doOpen jest wymagane; przy 1 - zabronione. Przy stylu PULSE pole pulseMs (czas impulsu w milisekundach, > 0) jest wymagane; przy MAINTAINED - zabronione.' },
      { kind: 'heading', text: 'Nadzor i stan bezpieczny' },
      { kind: 'p', text: 'confirmTimeoutMs to czas (co najmniej 100 ms - ponizej tego progu nadzor przestaje miec sens wobec realnego czasu dzialania sprzetu) na potwierdzenie zmiany stanu przez wejscie zwrotne, zanim zglaszany jest alarm rozbieznosci (discrepancyAlarm) - ROZBIEZNOSC to sytuacja, gdy polecenie zostalo wyslane, ale wejscie zwrotne nie potwierdzilo go w tym czasie (PRZEKROCZENIE CZASU to samo zdarzenie nazwane od strony zegara; discrepancyAlarm to, czy w ogole zglaszac to jako alarm). safeState.onStartup i onLinkLoss (NO_CHANGE/OPEN/CLOSE) opisuja, co MA ZROBIC SPRZET w tych sytuacjach - patrz [[intro-principle|1.3]].' },
      { kind: 'note', text: 'switchCounter (licznik przelaczen) celowo NIE MA wlasnego progu ostrzegawczego w tym kontrakcie - prog definiuje sie w EPW-Logic-Studio, odczytujac sygnal .COUNTER ([[dev-signals-commands|4.9]]). Prog ostrzegawczy wbudowany w konfiguracje sprzetu bylby ukryta logika wewnatrz opisu sprzetu - to swiadoma decyzja projektowa, nie brak funkcji.' },
    ],
    en: [
      { kind: 'p', text: 'SWITCHED is a controllable two-state device: a contactor, a valve, a damper. It has feedback, a command output, supervision and a safe state.' },
      { kind: 'heading', text: 'Feedback (feedback.mode)' },
      { kind: 'p', text: 'DUAL mode uses two digital inputs (diClosed and diOpen), which distinguishes four states:' },
      { kind: 'table', headers: ['diClosed', 'diOpen', 'Meaning'], rows: [
        ['0', '1', 'Open'],
        ['1', '0', 'Closed'],
        ['0', '0', 'In motion, or a broken wire'],
        ['1', '1', 'Fault (both limit switches at once)'],
      ] },
      { kind: 'p', text: 'SINGLE mode uses one input (diClosed) with optional negation (invert) and does NOT DISTINGUISH an intermediate state or a dead signal from OFF - that is a deliberate limitation of this mode, not a defect. NONE mode has no feedback input at all: control runs open-loop, the screen will never confirm the device\'s actual state.' },
      { kind: 'heading', text: 'Command' },
      { kind: 'p', text: 'The output count (1 or 2) and the style (MAINTAINED or PULSE) together give four combinations, each implying a real circuit:' },
      { kind: 'list', items: [
        '1 output, MAINTAINED - a typical contactor/valve with one coil held energized in the ON state.',
        '1 output, PULSE - a typical bistable relay driven by a short pulse.',
        '2 outputs, MAINTAINED - a typical three-position valve with separate OPEN/CLOSE coils.',
        '2 outputs, PULSE - a typical bistable contactor with separate ON/OFF pulses.',
      ] },
      { kind: 'p', text: 'With 2 outputs, doOpen is required; with 1, it is forbidden. With PULSE style, pulseMs (the pulse time in milliseconds, > 0) is required; with MAINTAINED, it is forbidden.' },
      { kind: 'heading', text: 'Supervision and safe state' },
      { kind: 'p', text: 'confirmTimeoutMs is the time (at least 100 ms - below that, supervision stops meaning anything against a real device\'s actual actuation time) allowed for feedback to confirm a state change before a discrepancy is reported (discrepancyAlarm) - a DISCREPANCY is a command that was sent but that feedback did not confirm within that time (a TIMEOUT is the same event named from the clock\'s side; discrepancyAlarm is whether to actually raise it as an alarm at all). safeState.onStartup and onLinkLoss (NO_CHANGE/OPEN/CLOSE) describe what THE HARDWARE ITSELF should do in those situations - see [[intro-principle|1.3]].' },
      { kind: 'note', text: 'switchCounter deliberately has NO warning-threshold field of its own in this contract - the threshold is defined in EPW-Logic-Studio, by reading the .COUNTER signal ([[dev-signals-commands|4.9]]). A warning threshold baked into the hardware configuration would be hidden logic inside a hardware description - a deliberate design decision, not a missing feature.' },
    ],
  },
  'dev-signal': {
    pl: [
      { kind: 'p', text: 'SIGNAL to urzadzenie wylacznie sygnalizacyjne, bez wyjscia sterujacego: lampka, stycznik pomocniczy uzywany jako czujnik, wylacznik krancowy raportujacy stan bez mozliwosci sterowania z ekranu.' },
      { kind: 'p', text: 'Pola: feedback.di (jedno wejscie cyfrowe) z opcjonalnym invert, alarmState (HIGH albo LOW - ktory POZIOM sygnalu liczy sie jako alarmowy) i debounceMs (opoznienie antydrganiowe, >= 0).' },
      { kind: 'p', text: 'W przeciwienstwie do SWITCHED, SIGNAL nie ma zadnego pola command - nie da sie z niego nic wyslac do sprzetu. To celowe: SIGNAL istnieje po to, zeby cos POKAZYWAC, nigdy zeby czyms STEROWAC.' },
    ],
    en: [
      { kind: 'p', text: 'SIGNAL is a signalling-only device, with no command output: an indicator lamp, an auxiliary contact used as a sensor, a limit switch reporting state with no way to control it from the screen.' },
      { kind: 'p', text: 'Fields: feedback.di (one digital input) with optional invert, alarmState (HIGH or LOW - which signal LEVEL counts as alarm) and debounceMs (anti-chatter delay, >= 0).' },
      { kind: 'p', text: 'Unlike SWITCHED, SIGNAL has no command field at all - nothing can be sent from it to the hardware. That is deliberate: SIGNAL exists to SHOW something, never to CONTROL something.' },
    ],
  },
  'dev-measured': {
    pl: [
      { kind: 'p', text: 'MEASURED to wejscie pomiarowe analogowe: temperatura, cisnienie, przeplyw. Pola: input (adres kanalu AI), unit (jednostka, np. "°C"), rangeMin/rangeMax (zakres, rangeMin musi byc mniejszy niz rangeMax), format (np. "0.0" - liczba cyfr po kropce odpowiada liczbie zer w tym tekscie) i deadband (strefa martwa wokol wartosci, >= 0).' },
      { kind: 'p', text: 'Edytor nie ma zywych danych, wiec podglad w formularzu pokazuje SRODEK skonfigurowanego zakresu (np. 0..400 daje podglad 200), sformatowany zgodnie z polem format - nigdy zmyslonej liczby.' },
      { kind: 'p', text: 'Kreator miernika ([[elem-meter|7.1]]) pokazuje wylacznie aparaty MEASURED, pogrupowane po jednostce - dlatego aparat musi istniec i miec zachowanie MEASURED, zanim pojawi sie na liscie do wyboru w kreatorze.' },
    ],
    en: [
      { kind: 'p', text: 'MEASURED is an analog measurement input: temperature, pressure, flow. Fields: input (an AI channel address), unit (e.g. "°C"), rangeMin/rangeMax (the range, rangeMin must be less than rangeMax), format (e.g. "0.0" - the digit count after the dot matches the number of zeros in that text) and deadband (a dead band around the value, >= 0).' },
      { kind: 'p', text: 'The editor has no live data, so the form\'s own preview shows the MIDDLE of the configured range (e.g. 0..400 previews as 200), formatted per the format field - never a made-up number.' },
      { kind: 'p', text: 'The meter wizard ([[elem-meter|7.1]]) only ever shows MEASURED devices, grouped by unit - which is why a device must exist and have the MEASURED behavior before it appears in the wizard\'s own picker list.' },
    ],
  },
  'dev-modulated': {
    pl: [
      { kind: 'p', text: 'MODULATED to urzadzenie sterowalne plynnie: zawor modulujacy, falownik. Pola: setpointOutput (adres kanalu AO - wartosc zadana wysylana do sprzetu), opcjonalny feedbackInput (adres kanalu AI - rzeczywista pozycja/predkosc, jesli sprzet ja raportuje), unit, rangeMin/rangeMax, startupValue i safeValue (obie musza miescic sie w zakresie rangeMin..rangeMax).' },
      { kind: 'p', text: 'startupValue i safeValue to, tak jak safeState aparatu SWITCHED ([[dev-switched|4.4]]), wartosci nalezace do KONFIGURACJI SPRZETU, nie do logiki ekranu - opisuja, jaka wartosc aparat ma przyjac przy starcie i w stanie bezpiecznym.' },
    ],
    en: [
      { kind: 'p', text: 'MODULATED is a continuously controllable device: a modulating valve, a VFD. Fields: setpointOutput (an AO channel address - the setpoint sent to the hardware), an optional feedbackInput (an AI channel address - the actual position/speed, if the hardware reports it), unit, rangeMin/rangeMax, startupValue and safeValue (both must fall within rangeMin..rangeMax).' },
      { kind: 'p', text: 'startupValue and safeValue, just like a SWITCHED device\'s safeState ([[dev-switched|4.4]]), belong to the HARDWARE\'S OWN CONFIGURATION, not to the screen\'s logic - they describe what value the device should take on startup and in its safe state.' },
    ],
  },
  'dev-form-validation': {
    pl: [
      { kind: 'p', text: 'Formularz aparatu waliduje NA ZYWO, przy kazdej zmianie pola, przez `validateDeviceRegistry` (jedyne miejsce, gdzie jakakolwiek regula jest faktycznie rozstrzygana) - kazdy blad pojawia sie natychmiast pod polem, ktorego dotyczy, a przycisk Zapisz pozostaje wygaszony, dopoki istnieje choc jeden blad.' },
      { kind: 'p', text: 'Picker adresu kanalu wyszarza kazdy kanal juz zajety przez inny aparat, pokazujac jego identyfikator w nawiasie - dzieki temu kolizja kanalow jest praktycznie niemozliwa do przypadkowego wprowadzenia, mimo ze `CHANNEL_ADDRESS_COLLISION` formalnie nadal istnieje jako regula sprawdzana przy zapisie.' },
      { kind: 'p', text: 'Pole Id jest edytowalne tylko przy tworzeniu nowego aparatu (rozwijana lista lokalizacji + wolny sufiks) i zablokowane przy edycji istniejacego - powod jest w [[dev-naming|4.2]].' },
    ],
    en: [
      { kind: 'p', text: 'The device form validates LIVE, on every field change, through `validateDeviceRegistry` (the only place any rule is actually decided) - every error appears immediately under the field it is about, and the Save button stays disabled while even one error exists.' },
      { kind: 'p', text: 'The channel address picker greys out any channel another device already occupies, showing its id in parentheses - which makes a channel collision practically impossible to enter by accident, even though `CHANNEL_ADDRESS_COLLISION` still formally exists as a rule checked at save time.' },
      { kind: 'p', text: 'The Id field is only editable when creating a new device (a location dropdown plus a free suffix) and is disabled when editing an existing one - the reason is in [[dev-naming|4.2]].' },
    ],
  },
  'dev-signals-commands': {
    pl: [
      { kind: 'p', text: 'Kazdy aparat udostepnia logice sterowania w EPW-Logic-Studio zestaw sygnalow, komend i - dla niektorych zachowan - sygnalow zakazu (INHIBIT), wyliczany WYLACZNIE z pola behavior (nigdy osobno deklarowany).' },
      { kind: 'table', headers: ['Zachowanie', 'Sygnaly (odczyt)', 'Komendy (zapis)'], rows: [
        ['SWITCHED', 'stan (otwarty/zamkniety/w ruchu/blad), rozbieznosc, .COUNTER (jesli wlaczony)', 'OTWORZ / ZAMKNIJ'],
        ['SIGNAL', 'stan alarmowy', '(brak)'],
        ['MEASURED', 'wartosc pomiaru', '(brak)'],
        ['MODULATED', 'wartosc zadana, wartosc zwrotna (jesli skonfigurowana)', 'ustaw wartosc'],
      ] },
      { kind: 'p', text: 'Sygnaly zakazu (INHIBIT) istnieja po to, zeby logika mogla ZABRONIC wykonania polecenia, nie tylko je wyslac. Bez nich logika sterowania umie ZALACZYC aparat, ale nie umie go ZABLOKOWAC przed poleceniem, ktore operator wysyla wprost z ekranu - polecenie operatora idzie wtedy prosto na wyjscie, bez mozliwosci przechwycenia go przez blokade logiki.' },
    ],
    en: [
      { kind: 'p', text: 'Every device exposes a set of signals, commands and - for some behaviors - inhibit signals to EPW-Logic-Studio\'s control logic, derived ENTIRELY from the behavior field (never separately declared).' },
      { kind: 'table', headers: ['Behavior', 'Signals (read)', 'Commands (write)'], rows: [
        ['SWITCHED', 'state (open/closed/moving/fault), discrepancy, .COUNTER (if enabled)', 'OPEN / CLOSE'],
        ['SIGNAL', 'alarm state', '(none)'],
        ['MEASURED', 'measured value', '(none)'],
        ['MODULATED', 'setpoint, feedback value (if configured)', 'set value'],
      ] },
      { kind: 'p', text: 'Inhibit signals exist so logic can FORBID a command from executing, not only send one. Without them, control logic can TURN a device ON, but cannot BLOCK it from a command the operator sends straight from the screen - the operator\'s command then goes directly to the output, with no way for a logic interlock to intercept it.' },
    ],
  },
};
