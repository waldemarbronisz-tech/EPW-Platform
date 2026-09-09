// feat/help-system commit 5 - full content for chapters 9-12, Polish and
// English (originally 8-12; chapter 8, the isometric PLAN screen, was
// removed in full by chore/remove-isometric-plan-mode along with the
// mode itself - see HelpToc.ts's own comment on the resulting gap in
// chapter numbering). Checked against historySlice.ts, CanvasView.ts,
// Canvas.tsx's own keydown handler, and ProjectSchema.ts/Migrations.ts/
// ProjectV2Schema.ts.

import type { HelpContentMap } from './HelpContentRegistry';

export const HELP_CONTENT_OPERATIONS: HelpContentMap = {
  // ==================== CHAPTER 9 - WORKING WITH THE EDITOR ====================
  'edit-selection': {
    pl: [
      { kind: 'p', text: 'Klikniecie zaznacza pojedynczy element (obiekt, przewod, miernik, panel albo ramke); Shift+klik dodaje albo usuwa element z biezacego zaznaczenia. Przeciagniecie po pustym miejscu plotna rysuje ramke zaznaczenia - obejmuje kazdy element CALKOWICIE w niej zawarty.' },
      { kind: 'p', text: 'Ctrl+A (albo Cmd+A) zaznacza wszystko na biezacym ekranie naraz - obiekty, przewody i mierniki razem. Zaznaczenie jest zawsze jednego "rodzaju" na raz w typowym uzyciu: Properties pokazuje "Multiple objects selected" zamiast szczegolow, jesli zaznaczenie miesza wiecej niz jeden rodzaj elementow.' },
    ],
    en: [
      { kind: 'p', text: 'A click selects a single element (an object, a wire, a meter, a panel or a frame); Shift+click adds or removes an element from the current selection. Dragging on empty canvas draws a selection box - it picks up every element ENTIRELY contained within it.' },
      { kind: 'p', text: 'Ctrl+A (or Cmd+A) selects everything on the current screen at once - objects, wires and meters together. In typical use a selection is always one "kind" at a time: Properties shows "Multiple objects selected" instead of details when the selection mixes more than one kind of element.' },
    ],
  },
  'edit-moving-snap': {
    pl: [
      { kind: 'p', text: 'Przeciagniecie zaznaczonych elementow przesuwa je; jesli przyciaganie do siatki jest wlaczone (menu View > Snap to Grid, domyslnie wlaczone), pozycja jest zaokraglana do najblizszego oczka siatki. Przytrzymanie Alt podczas przeciagania CHWILOWO wylacza przyciaganie, niezaleznie od stanu przelacznika w menu.' },
      { kind: 'p', text: 'Klawisze strzalek przesuwaja zaznaczenie o jedno oczko siatki na nacisniecie, o dziesiec oczek z wcisnietym Shift - kazde nacisniecie (wliczajac powtorzenia z przytrzymanego klawisza) to osobny wpis w historii cofniec.' },
    ],
    en: [
      { kind: 'p', text: 'Dragging selected elements moves them; if snap-to-grid is on (View menu > Snap to Grid, on by default), the position rounds to the nearest grid cell. Holding Alt while dragging TEMPORARILY disables snapping, regardless of the menu toggle\'s own state.' },
      { kind: 'p', text: 'Arrow keys move the selection by one grid cell per press, ten cells with Shift held - every press (including repeats from a held key) is its own entry in the undo history.' },
    ],
  },
  'edit-copy-paste-duplicate': {
    pl: [
      { kind: 'p', text: 'Ctrl+C kopiuje biezace zaznaczenie (obiekty, przewody i mierniki razem, cokolwiek jest akurat niepuste) do wewnetrznego schowka edytora. Ctrl+V wkleja, przesuwajac wklejone elementy o dokladnie jedno oczko siatki w prawo i w dol wzgledem oryginalu - zeby kopia nigdy nie ladowala sie idealnie na oryginale, niewidoczna.' },
      { kind: 'p', text: 'Ctrl+D powiela zaznaczenie W MIEJSCU, z tym samym przesunieciem co wklejanie, ale bez dotykania schowka - schowek pozostaje z tym, co bylo skopiowane wczesniej.' },
      { kind: 'p', text: 'Alt+przeciagniecie to trzeci sposob: zostawia CICHA kopie dokladnie w miejscu, z ktorego zaczeto przeciagac (bez zaznaczenia, bez wpisu do historii samej w sobie), podczas gdy oryginalny element kontynuuje przeciaganie pod kursorem - cale zdarzenie (kopia + przesuniecie) liczy sie jako jedno dzialanie w historii.' },
    ],
    en: [
      { kind: 'p', text: 'Ctrl+C copies the current selection (objects, wires and meters together, whichever is non-empty) to the editor\'s own internal clipboard. Ctrl+V pastes it, offsetting the pasted elements by exactly one grid cell right and down from the original - so a paste never lands invisibly right on top of the original.' },
      { kind: 'p', text: 'Ctrl+D duplicates the selection IN PLACE, with the same offset paste uses, without touching the clipboard - the clipboard keeps whatever was copied earlier.' },
      { kind: 'p', text: 'Alt+drag is a third way: it leaves a SILENT copy exactly where the drag started (unselected, no history entry of its own), while the original element keeps being dragged under the cursor - the whole event (the copy plus the move) counts as one action in the history.' },
    ],
  },
  'edit-undo-redo': {
    pl: [
      { kind: 'p', text: 'Historia cofniec obejmuje LACZNIE obiekty, przewody, mierniki, panele sygnalizacyjne i ramki jako JEDEN migawkowy zapis na kazde wywolanie zapisu historii - nie osobna historie dla kazdego typu elementu. Limit to 100 wpisow.' },
      { kind: 'p', text: 'JEDNO dzialanie w historii to: jedno przeciagniecie (od nacisniecia do puszczenia przycisku myszy), jedno nacisniecie strzalki, jedna operacja z menu (Wytnij/Wklej/Usun), jedno zakonczone rysowanie przewodu. Proba zapisu, w ktorej nic sie faktycznie nie zmienilo (np. klikniecie w pole i wyjscie bez edycji), jest pomijana, zeby nie zaśmiecac historii pustymi wpisami.' },
      { kind: 'p', text: 'Rejestry projektu (lokalizacje, karty, aparaty) oraz wybrany jezyk pomocy NIE naleza do tej historii cofniec - sa to ustawienia projektu, a nie tresc rysunku; ich zmiany nie da sie cofnac przez Ctrl+Z z poziomu menu Edit.' },
    ],
    en: [
      { kind: 'p', text: 'Undo history covers objects, wires, meters, signal panels and frames TOGETHER as ONE combined snapshot per history-save call - not a separate history per element type. The limit is 100 entries.' },
      { kind: 'p', text: 'ONE action in the history is: one drag (from mouse-down to mouse-up), one arrow-key press, one menu operation (Copy/Paste/Delete), one finished wire drawing. An attempt to save history where nothing actually changed (e.g. clicking into a field and leaving without editing it) is skipped, so it does not clutter the history with empty entries.' },
      { kind: 'p', text: 'The project registries (locations, cards, devices) and the chosen help language are NOT part of this undo history - they are project settings, not drawing content; their changes cannot be undone through the Edit menu\'s undo.' },
    ],
  },
  'edit-pan-zoom': {
    pl: [
      { kind: 'p', text: 'Przytrzymanie spacji zamienia kursor w reke i pozwala przewijac plotno przeciagnieciem lewym przyciskiem myszy - dziala tak samo na obu rodzajach ekranu.' },
      { kind: 'p', text: 'Ctrl+0 przywraca skale do 100% BEZ zmiany przewiniecia (pan pozostaje dokladnie tam, gdzie byl); Ctrl+9 dopasowuje jednoczesnie skale i przewiniecie, zeby zmiescic cala zawartosc projektu w biezacym oknie.' },
    ],
    en: [
      { kind: 'p', text: 'Holding Space turns the cursor into a hand and lets a left-button drag pan the canvas - this works the same way on both screen kinds.' },
      { kind: 'p', text: 'Ctrl+0 restores 100% zoom WITHOUT changing the pan (it stays exactly where it was); Ctrl+9 adjusts both zoom and pan together to fit the whole project\'s content into the current viewport.' },
    ],
  },
  'edit-layers': {
    pl: [
      { kind: 'p', text: 'Rysowanie na schemacie odbywa sie w ustalonych warstwach, zawsze w tej samej kolejnosci: przewody i wezly, potem symbole/mierniki/panele, potem etykiety (osobny przebieg PO wszystkich symbolach), a na samej gorze zaznaczenie i uchwyty transformacji.' },
      { kind: 'p', text: 'Etykieta jest rysowana w OSOBNYM, pozniejszym przebiegu po wszystkich symbolach wlasnie po to, zeby etykieta jednego obiektu nigdy nie schowala sie pod symbolem innego, sasiedniego obiektu - kolejnosc w tablicy obiektow nie ma tu znaczenia, warstwa etykiet zawsze jest ponad warstwa symboli w calosci.' },
    ],
    en: [
      { kind: 'p', text: 'Drawing on the schematic happens in fixed layers, always in the same order: wires and junctions, then symbols/meters/panels, then labels (a separate pass AFTER every symbol), and selection and transform handles on top of everything.' },
      { kind: 'p', text: 'A label is drawn in a SEPARATE, later pass after every symbol precisely so one object\'s label never falls under a different, neighboring object\'s symbol - the objects\' own array order does not matter here, the label layer is always entirely above the symbol layer.' },
    ],
  },
  'edit-messages-panel': {
    pl: [
      { kind: 'p', text: 'Panel Messages, u dolu okna, zbiera komunikaty z calego edytora: informacje (np. "Project created: ..."), ostrzezenia (np. symbol wskazujacy na nieistniejacy aparat - [[sym-device-binding|6.4]]) i bledy (np. nieudany zapis projektu z powodu bledu walidacji). Kazdy wpis ma znacznik czasu.' },
      { kind: 'p', text: 'Waga komunikatu jest rozpoznawana z prefiksu tekstu: `[ERROR]` i `[WARNING]` na poczatku wiadomosci nadaja jej odpowiednio kolor bledu albo ostrzezenia; kazdy inny tekst trafia jako zwykla informacja.' },
    ],
    en: [
      { kind: 'p', text: 'The Messages panel, at the bottom of the window, collects messages from across the editor: info (e.g. "Project created: ..."), warnings (e.g. a symbol pointing at a nonexistent device - [[sym-device-binding|6.4]]) and errors (e.g. a failed project save due to a validation error). Every entry carries a timestamp.' },
      { kind: 'p', text: 'A message\'s severity is read from a text prefix: `[ERROR]` and `[WARNING]` at the start of the message color it as an error or a warning respectively; any other text is filed as plain info.' },
    ],
  },

  // ==================== CHAPTER 10 - FILE FORMAT ====================
  'file-contents': {
    pl: [
      { kind: 'p', text: 'Plik projektu (`.epwsyn`, JSON) ma pole `format: "EPW_SYNOPTIC"` i `schema_version`. Zawiera: metadane projektu, konfiguracje kanwy, tablice `objects` i `connections`, opcjonalnie `meters`, `signalPanels`, `frames`, `devices`, `locations`, `cards`, `kind` (rodzaj ekranu - dzis zawsze SCHEMATIC, patrz [[intro-screens|1.4]]) i `helpLanguage` (jezyk pomocy).' },
      { kind: 'p', text: 'Kazde z pol opcjonalnych zostalo dodane w ten sam sposob: dopisane jako nowe pole bez podnoszenia numeru wersji schematu, bo starszy plik po prostu nie ma tego pola i wczytuje sie z sensowna wartoscia domyslna (pusta tablica/mapa, jezyk polski) zamiast bledu.' },
      { kind: 'note', text: 'W repozytorium istnieje TAKZE drugi, niezalezny format o nazwie EPW_PROJECT (plik `ProjectV2Schema.ts`), z zupelnie innym modelem (wiele ekranow w jednym pliku, polaczenia oparte na portach zamiast na wezlach). Nic w dzialajacym edytorze go dzis nie zapisuje ani nie odczytuje - to wylacznie definicje typow i walidator, przygotowanie pod przyszla architekture, nie aktywny format.' },
    ],
    en: [
      { kind: 'p', text: 'The project file (`.epwsyn`, JSON) has a `format: "EPW_SYNOPTIC"` field and a `schema_version`. It contains: project metadata, canvas configuration, `objects` and `connections` arrays, and optionally `meters`, `signalPanels`, `frames`, `devices`, `locations`, `cards`, `kind` (the screen kind - always SCHEMATIC today, see [[intro-screens|1.4]]) and `helpLanguage` (the help language).' },
      { kind: 'p', text: 'Every optional field was added the same way: appended as a new field without bumping the schema version, because an older file simply has none of it and loads with a sensible default (an empty array/map, Polish) instead of an error.' },
      { kind: 'note', text: 'A SECOND, independent format called EPW_PROJECT also exists in this repository (`ProjectV2Schema.ts`), with a completely different model (multiple screens in one file, port-based rather than node-based connections). Nothing in the running editor writes or reads it today - it is type definitions and a validator only, groundwork for a future architecture, not an active format.' },
    ],
  },
  'file-versioning': {
    pl: [
      { kind: 'p', text: '`CURRENT_SCHEMA_VERSION` (w `ProjectSchema.ts`) rosnie wylacznie przy zmianie niezgodnej wstecz - np. przejscie z modelu polaczen opartego na portach na model wezlowy podniosl wersje z 1 na 2. Kazda taka zmiana ma wlasna migracje (`Migrations.ts`), ktora przeksztalca starszy plik do biezacego ksztaltu przy wczytaniu.' },
      { kind: 'p', text: 'Plik z numerem wersji WYZSZYM niz obslugiwany przez biezaca wersje edytora jest odrzucany od razu, z komunikatem bledu - nigdy nie jest wczytywany czesciowo ani "najlepiej jak sie da".' },
    ],
    en: [
      { kind: 'p', text: '`CURRENT_SCHEMA_VERSION` (in `ProjectSchema.ts`) only increases on a backward-incompatible change - e.g. moving from the port-based connection model to the node-based one bumped it from 1 to 2. Every such change has its own migration (`Migrations.ts`) that reshapes an older file into the current shape on load.' },
      { kind: 'p', text: 'A file with a version number HIGHER than the current editor build supports is rejected outright, with an error - it is never partially loaded or loaded "best-effort".' },
    ],
  },
  'file-guarantees': {
    pl: [
      { kind: 'p', text: 'Edytor gwarantuje: ksztalt danych zgodny z `validateProjectSchema` (obiekty maja identyfikatory, przewody maja co najmniej dwa punkty i tylko odcinki poziome/pionowe, poprawne wartosci pol enum) oraz ksztalt i reguly rejestru aparatow zgodne z `validateDeviceRegistry` przy kazdym zapisie z poziomu formularza aparatu.' },
      { kind: 'p', text: 'Edytor NIE gwarantuje: ze projekt "zadziala" na prawdziwym sprzecie, ze kazdy aparat jest FAKTYCZNIE podlaczony do czegokolwiek w symbolach na ekranie (aparat bez zadnego przypisanego symbolu jest w pelni poprawny), ani ze dane wpisane w polu Editor Preview maja cokolwiek wspolnego z rzeczywistym stanem instalacji - patrz [[intro-what|1.1]].' },
    ],
    en: [
      { kind: 'p', text: 'The editor guarantees: a data shape matching `validateProjectSchema` (objects have ids, wires have at least two points and only horizontal/vertical segments, valid enum field values) and a device registry shape and set of rules matching `validateDeviceRegistry` on every save from the device form.' },
      { kind: 'p', text: 'The editor does NOT guarantee: that the project "works" on real hardware, that every device is ACTUALLY connected to anything among the screen\'s symbols (a device with no symbol assigned to it at all is fully valid), or that data typed into the Editor Preview field has anything to do with the installation\'s real state - see [[intro-what|1.1]].' },
    ],
  },
  'file-epwos-bridge': {
    pl: [
      { kind: 'p', text: 'NIE, nie w pelni - sprawdzone bezposrednio w kodzie EPW-OS. Istnieje tam `SynopticRuntimeAdapter` (`epw_os/gui/widgets/synoptic_runtime.py`), ktory sprawdza pole `format === "EPW_SYNOPTIC"` i wczytuje tablice `objects` - ale to jawnie oznaczony w kodzie "uproszczony, mockowy" szkielet.' },
      { kind: 'p', text: 'Ten szkielet NIE czyta w ogole `connections` (czyli calego modelu wezlowego, [[sch-node-model|5.1]]), NIE czyta `devices`/`locations`/`cards` (calego rejestru aparatow, rozdzial 4), a jego wlasna obsluga kliknieca zaklada, ze `bindings.command` to zwykly tekst w postaci "cel.akcja" - podczas gdy w tym edytorze `bindings.command` to obiekt `{tag, data_type, access}`, nie tekst. Wywolanie tej sciezki dzisiaj skonczyloby sie bledem, nie dzialaniem.' },
      { kind: 'p', text: 'Komentarz we wlasnym kodzie EPW-OS (`epw_os/gui/main_window.py`) mowi to wprost: strona glowna "bedzie hostowac przelaczalne ekrany synoptyki, gdy integracja z Synoptic Editor wyladuje" - czyli jeszcze nie wyladowala. Most miedzy plikiem tego edytora a dzialajacym ekranem w EPW-OS jeszcze nie istnieje.' },
    ],
    en: [
      { kind: 'p', text: 'NO, not fully - checked directly in EPW-OS\'s own code. It has a `SynopticRuntimeAdapter` (`epw_os/gui/widgets/synoptic_runtime.py`) that checks `format === "EPW_SYNOPTIC"` and loads the `objects` array - but that is explicitly labeled in its own code as a "simplified mock" skeleton.' },
      { kind: 'p', text: 'That skeleton does NOT read `connections` at all (the whole node-based wiring model, [[sch-node-model|5.1]]), does NOT read `devices`/`locations`/`cards` (the whole device registry, chapter 4), and its own click handling assumes `bindings.command` is plain "target.action" text - while in this editor `bindings.command` is an object `{tag, data_type, access}`, not text. Exercising that path today would end in an error, not in working behavior.' },
      { kind: 'p', text: 'EPW-OS\'s own code comment (`epw_os/gui/main_window.py`) says it outright: its main page "will host switchable synoptic screens once the Synoptic Editor integration lands" - meaning it has not landed yet. The bridge from this editor\'s file to a live screen in EPW-OS does not exist yet.' },
    ],
  },

  // ==================== CHAPTER 11 - TROUBLESHOOTING ====================
  'ts-meter-wizard-empty': {
    pl: [
      { kind: 'p', text: 'OBJAW: kreator miernika (przycisk Kreator... przy elemencie Miernik) pokazuje pusta liste zamiast aparatow do wyboru.' },
      { kind: 'p', text: 'PRZYCZYNA: kreator pokazuje WYLACZNIE aparaty o zachowaniu MEASURED ([[dev-measured|4.6]]) - jesli w projekcie nie ma jeszcze zadnego takiego aparatu (albo istniejace maja inne zachowanie), lista jest pusta.' },
      { kind: 'p', text: 'CO ZROBIC: Aparaty > Lista aparatow... > + Dodaj, ustaw Zachowanie na MEASURED, wypelnij i zapisz. Miernik trzeba zamknac i otworzyc kreator ponownie, zeby zobaczyc nowo dodany aparat.' },
    ],
    en: [
      { kind: 'p', text: 'SYMPTOM: the meter wizard (the Kreator... button on a Meter element) shows an empty list instead of devices to choose from.' },
      { kind: 'p', text: 'CAUSE: the wizard shows ONLY devices with the MEASURED behavior ([[dev-measured|4.6]]) - if the project has no such device yet (or existing ones have a different behavior), the list is empty.' },
      { kind: 'p', text: 'FIX: Aparaty > Lista aparatow... > + Dodaj, set Behavior to MEASURED, fill it in and save. Close and reopen the wizard to see the newly added device.' },
    ],
  },
  'ts-cannot-connect-wire-symbol': {
    pl: [
      { kind: 'p', text: 'OBJAW: przewod konczy sie obok symbolu, ale nie wyglada na polaczony (nie ma kropki wezlowej, siec nie obejmuje symbolu).' },
      { kind: 'p', text: 'PRZYCZYNA: polaczenie powstaje wylacznie z DOKLADNEGO dotkniecia punktu siatki zacisku ([[sch-node-model|5.1]]) - jesli koniec przewodu ladowal o piksel obok, geometrycznie nie stykaja sie w ogole, mimo ze wizualnie wygladaja blisko.' },
      { kind: 'p', text: 'CO ZROBIC: upewnij sie, ze przyciaganie do siatki jest wlaczone (View > Snap to Grid), oddal/przybliz widok, zeby dokladnie trafic w widoczny znacznik zacisku (pojawia sie przy najechaniu na symbol), i zakoncz tam rysowanie przewodu.' },
    ],
    en: [
      { kind: 'p', text: 'SYMPTOM: a wire ends near a symbol, but does not look connected (no junction dot, the net does not include the symbol).' },
      { kind: 'p', text: 'CAUSE: a connection only forms from an EXACT touch of the terminal\'s grid point ([[sch-node-model|5.1]]) - if the wire\'s end landed one pixel off, they do not touch geometrically at all, even though they look close visually.' },
      { kind: 'p', text: 'FIX: make sure snap-to-grid is on (View > Snap to Grid), zoom in/out to land exactly on the visible terminal marker (shown on hovering the symbol), and end the wire drawing there.' },
    ],
  },
  'ts-wire-not-joining-busbar': {
    pl: [
      { kind: 'p', text: 'OBJAW: nowy przewod przebiega obok szyny zbiorczej, ale nie liczy sie z nia do jednej sieci.' },
      { kind: 'p', text: 'PRZYCZYNA: dotkniecie musi wypasc DOKLADNIE na odcinku szyny (dowolny punkt jej dlugosci, ale musi lezec na niej geometrycznie), a nie tylko blisko niej - patrz [[sch-wire-style|5.4]].' },
      { kind: 'p', text: 'CO ZROBIC: powieksz widok wokol szyny, upewnij sie ze przyciaganie do siatki jest wlaczone, i zakoncz (albo zacznij) przewod dokladnie na punkcie lezacym na linii szyny.' },
    ],
    en: [
      { kind: 'p', text: 'SYMPTOM: a new wire runs near the busbar, but does not count as part of its net.' },
      { kind: 'p', text: 'CAUSE: the touch must land EXACTLY on the busbar\'s segment (any point along its length, but it must lie on it geometrically), not merely close to it - see [[sch-wire-style|5.4]].' },
      { kind: 'p', text: 'FIX: zoom in around the busbar, make sure snap-to-grid is on, and end (or start) the wire exactly on a point lying on the busbar\'s line.' },
    ],
  },
  'ts-device-marked-invalid': {
    pl: [
      { kind: 'p', text: 'OBJAW: wiersz aparatu w Liscie aparatow jest pokazany kolorem alarmowym.' },
      { kind: 'p', text: 'PRZYCZYNA: `validateDeviceRegistry` znalazl co najmniej jeden blad dla tego aparatu - najedz kursorem na wiersz, zeby zobaczyc dokladna tresc bledu w dymku.' },
      { kind: 'p', text: 'CO ZROBIC: otworz aparat do edycji (Edytuj) - kazdy blad pojawi sie tez bezposrednio pod polem, ktorego dotyczy ([[dev-form-validation|4.8]]), z tym samym tekstem co dymek w liscie.' },
    ],
    en: [
      { kind: 'p', text: 'SYMPTOM: a device\'s row in the Device List is shown in the alarm color.' },
      { kind: 'p', text: 'CAUSE: `validateDeviceRegistry` found at least one error for that device - hover the row to see the exact error text in its tooltip.' },
      { kind: 'p', text: 'FIX: open the device for editing (Edytuj) - every error also appears directly under the field it is about ([[dev-form-validation|4.8]]), with the same text as the list\'s tooltip.' },
    ],
  },
  'ts-channel-unavailable': {
    pl: [
      { kind: 'p', text: 'OBJAW: w pickerze adresu kanalu wybrany numer jest wyszarzony i nie da sie go wybrac.' },
      { kind: 'p', text: 'PRZYCZYNA: ten kanal jest juz uzywany przez inny aparat - identyfikator tego aparatu jest pokazany w nawiasie obok numeru kanalu.' },
      { kind: 'p', text: 'CO ZROBIC: wybierz inny wolny kanal, albo jesli to bylo przez pomylke, otworz wskazany aparat i zwolnij ten kanal tam (zmien jego adres na inny).' },
    ],
    en: [
      { kind: 'p', text: 'SYMPTOM: a channel number is greyed out in the channel address picker and cannot be selected.' },
      { kind: 'p', text: 'CAUSE: that channel is already used by another device - that device\'s id is shown in parentheses next to the channel number.' },
      { kind: 'p', text: 'FIX: pick a different free channel, or if that was a mistake, open the device named there and free that channel by changing its address to something else.' },
    ],
  },
  'ts-symbol-red-outline': {
    pl: [
      { kind: 'p', text: 'OBJAW: symbol na schemacie ma przerywana czerwona obwodke, chociaz renderuje sie normalnie poza tym.' },
      { kind: 'p', text: 'PRZYCZYNA: pole Aparat tego symbolu wskazuje na identyfikator, ktorego nie ma juz w rejestrze aparatow - najczesciej dlatego, ze ten aparat zostal usuniety z Listy aparatow po tym, jak symbol juz na niego wskazywal. W panelu Messages powinno byc odpowiadajace ostrzezenie.' },
      { kind: 'p', text: 'CO ZROBIC: zaznacz symbol, we Properties w polu Aparat wybierz wlasciwy aparat z listy (albo (brak), jesli symbol ma zostac czysta grafika), albo utworz na nowo aparat o tym samym identyfikatorze, jesli usuniecie bylo pomylka.' },
    ],
    en: [
      { kind: 'p', text: 'SYMPTOM: a schematic symbol has a dashed red outline, even though it otherwise renders normally.' },
      { kind: 'p', text: 'CAUSE: that symbol\'s Aparat field points at an id no longer present in the device registry - usually because that device was deleted from the Device List after the symbol had already been pointing at it. A matching warning should be in the Messages panel.' },
      { kind: 'p', text: 'FIX: select the symbol, pick the correct device from the Aparat dropdown in Properties (or (brak) if the symbol should become pure graphics), or recreate a device under the same id if the deletion was a mistake.' },
    ],
  },
  'ts-cannot-delete-location-card': {
    pl: [
      { kind: 'p', text: 'OBJAW: przycisk Usun przy lokalizacji albo karcie w Rejestrach projektu jest wygaszony.' },
      { kind: 'p', text: 'PRZYCZYNA: choc jeden aparat nadal uzywa tej lokalizacji (jej kod jest przedrostkiem jego identyfikatora) albo tej karty (jeden z jego adresow kanalow na nia wskazuje) - patrz [[reg-delete-protection|3.4]]. Najedz na przycisk, zeby zobaczyc liczbe i identyfikatory aparatow.' },
      { kind: 'p', text: 'CO ZROBIC: usun albo przenies (czyli utworz od nowa pod innym identyfikatorem - [[reg-locations|3.1]]) kazdy wymieniony aparat, zanim usuniesz lokalizacje albo karte.' },
    ],
    en: [
      { kind: 'p', text: 'SYMPTOM: the Delete button next to a location or card in Project Registries is disabled.' },
      { kind: 'p', text: 'CAUSE: at least one device still uses that location (its code is the prefix of the device\'s id) or that card (one of its channel addresses points at it) - see [[reg-delete-protection|3.4]]. Hover the button to see the count and the devices\' ids.' },
      { kind: 'p', text: 'FIX: delete or move (i.e. recreate under a different id - [[reg-locations|3.1]]) every listed device before deleting the location or card.' },
    ],
  },
  'ts-device-id-locked': {
    pl: [
      { kind: 'p', text: 'OBJAW: przy edycji istniejacego aparatu pole Id jest zaszarzone i nie da sie go zmienic.' },
      { kind: 'p', text: 'PRZYCZYNA: id jest niezmienny CELOWO - to klucz, po ktorym symbole na ekranie i wiersze mierzenikow/paneli odwoluja sie do aparatu ([[dev-naming|4.2]]). Edycja go na zywo popsulaby kazde takie odwolanie.' },
      { kind: 'p', text: 'CO ZROBIC: utworz nowy aparat z zadanym identyfikatorem, recznie przepisz do niego wartosci pol ze starego (Duplikuj czysci tylko id/oznaczenie, wiec moze pomoc jako punkt startowy), a potem usun stary aparat. Kazdy symbol wskazujacy na stary identyfikator trzeba bedzie recznie przepiac na nowy - usuniecie aparatu nie ostrzega, ile symboli na ekranie na niego wskazuje.' },
    ],
    en: [
      { kind: 'p', text: 'SYMPTOM: when editing an existing device, the Id field is greyed out and cannot be changed.' },
      { kind: 'p', text: 'CAUSE: the id is DELIBERATELY immutable - it is the key screen symbols and meter/panel rows reference the device by ([[dev-naming|4.2]]). Editing it live would break every such reference.' },
      { kind: 'p', text: 'FIX: create a new device with the desired id, copy the old one\'s field values into it by hand (Duplikuj only clears id/designation, so it can help as a starting point), then delete the old device. Every symbol pointing at the old id will need to be re-pointed at the new one by hand - deleting a device does not warn how many screen symbols reference it.' },
    ],
  },
  'ts-signal-panel-wizard-missing-device': {
    pl: [
      { kind: 'p', text: 'OBJAW: oczekiwany aparat nie pojawia sie na liscie w kreatorze panelu sygnalizacyjnego.' },
      { kind: 'p', text: 'PRZYCZYNA: ten kreator pokazuje wylacznie aparaty SIGNAL i SWITCHED ([[elem-signal-panel|7.2]]) - MEASURED i MODULATED nigdy sie tu nie pojawiaja, bo nie maja pojecia stanu dwustanowego do zasygnalizowania diodą.' },
      { kind: 'p', text: 'CO ZROBIC: sprawdz zachowanie tego aparatu w Liscie aparatow - jesli to MEASURED, nalezy do miernika ([[elem-meter|7.1]]), nie do panelu sygnalizacyjnego.' },
    ],
    en: [
      { kind: 'p', text: 'SYMPTOM: an expected device does not appear in the signal panel wizard\'s list.' },
      { kind: 'p', text: 'CAUSE: that wizard shows only SIGNAL and SWITCHED devices ([[elem-signal-panel|7.2]]) - MEASURED and MODULATED never appear here, since they have no two-state notion for a diode to signal.' },
      { kind: 'p', text: 'FIX: check that device\'s behavior in the Device List - if it is MEASURED, it belongs on a meter ([[elem-meter|7.1]]), not a signal panel.' },
    ],
  },
  'ts-save-disabled': {
    pl: [
      { kind: 'p', text: 'OBJAW: przycisk Zapisz w formularzu aparatu jest nieaktywny i nie reaguje na klikniecie.' },
      { kind: 'p', text: 'PRZYCZYNA: co najmniej jedno pole ma wciaz aktywny blad walidacji ([[dev-form-validation|4.8]]) - Zapisz pozostaje zablokowany, dopoki wszystkie znikna.' },
      { kind: 'p', text: 'CO ZROBIC: przewin formularz i znajdz kazdy czerwony tekst pod polami - zwykle jest ich wiecej niz jeden na raz przy nowo tworzonym aparacie.' },
    ],
    en: [
      { kind: 'p', text: 'SYMPTOM: the Save button in the device form is disabled and does not respond to clicking.' },
      { kind: 'p', text: 'CAUSE: at least one field still has an active validation error ([[dev-form-validation|4.8]]) - Save stays disabled until all of them are gone.' },
      { kind: 'p', text: 'FIX: scroll the form and find every red text under a field - there is usually more than one at once on a freshly created device.' },
    ],
  },
  'ts-designation-duplicate': {
    pl: [
      { kind: 'p', text: 'OBJAW: przy zapisie aparatu pojawia sie blad o zdublowanym oznaczeniu w danej lokalizacji.' },
      { kind: 'p', text: 'PRZYCZYNA: dwa aparaty w TEJ SAMEJ lokalizacji nie moga miec tego samego oznaczenia (`DEVICE_DUPLICATE_DESIGNATION_IN_LOCATION`) - to samo oznaczenie w DWOCH ROZNYCH lokalizacjach jest jednak jak najbardziej dozwolone.' },
      { kind: 'p', text: 'CO ZROBIC: zmien oznaczenie jednego z dwoch aparatow na unikalne w obrebie tej lokalizacji.' },
    ],
    en: [
      { kind: 'p', text: 'SYMPTOM: saving a device shows an error about a duplicate designation within a location.' },
      { kind: 'p', text: 'CAUSE: two devices in the SAME location cannot share a designation (`DEVICE_DUPLICATE_DESIGNATION_IN_LOCATION`) - the same designation in TWO DIFFERENT locations is, however, perfectly allowed.' },
      { kind: 'p', text: 'FIX: change one of the two devices\' designations to something unique within that location.' },
    ],
  },
  'ts-wire-diagonal-rejected': {
    pl: [
      { kind: 'p', text: 'OBJAW: przy rysowaniu przewodu ruch myszy po skosie nie daje odcinka po skosie, tylko dwa odcinki pod katem prostym.' },
      { kind: 'p', text: 'PRZYCZYNA: to nie usterka - kazdy odcinek przewodu MUSI byc poziomy albo pionowy (`appendWirePoint` w `WireDrawing.ts`); ruch po skosie jest automatycznie dzielony na poziomy odcinek, a potem pionowy, w jeden naroznik.' },
      { kind: 'p', text: 'CO ZROBIC: to zamierzone zachowanie - jesli potrzebny inny ksztalt naroznika, kliknij posrednie punkty, zeby samemu ustawic, gdzie przewod skreca.' },
    ],
    en: [
      { kind: 'p', text: 'SYMPTOM: while drawing a wire, a diagonal mouse movement never produces a diagonal segment, only two right-angle ones.' },
      { kind: 'p', text: 'CAUSE: this is not a defect - every wire segment MUST be horizontal or vertical (`appendWirePoint` in `WireDrawing.ts`); a diagonal movement is automatically split into a horizontal segment then a vertical one, forming one corner.' },
      { kind: 'p', text: 'FIX: this is intended behavior - if a different corner shape is needed, click intermediate points to control exactly where the wire turns.' },
    ],
  },
  'ts-project-wont-open': {
    pl: [
      { kind: 'p', text: 'OBJAW: File > Open... na wybranym pliku konczy sie komunikatem bledu zamiast otworzyc projekt.' },
      { kind: 'p', text: 'PRZYCZYNA: jedna z trzech mozliwosci - plik nie jest poprawnym JSON-em (blad parsowania), pole `format` nie jest rowne `"EPW_SYNOPTIC"` (to plik innego programu albo innego formatu, np. wspomniany w [[file-contents|10.1]] EPW_PROJECT), albo `schema_version` jest wyzszy niz obslugiwany przez ta wersje edytora ([[file-versioning|10.2]]).' },
      { kind: 'p', text: 'CO ZROBIC: przeczytaj dokladna tresc bledu w panelu Messages - kazdy z trzech przypadkow ma osobny, konkretny komunikat. Plik z za nowa wersja wymaga nowszej wersji edytora; zly format nie jest plikiem tego programu.' },
    ],
    en: [
      { kind: 'p', text: 'SYMPTOM: File > Open... on a chosen file ends in an error message instead of opening the project.' },
      { kind: 'p', text: 'CAUSE: one of three things - the file is not valid JSON (a parse error), the `format` field is not `"EPW_SYNOPTIC"` (it is a file from a different program or a different format, e.g. the EPW_PROJECT one mentioned in [[file-contents|10.1]]), or `schema_version` is higher than this editor build supports ([[file-versioning|10.2]]).' },
      { kind: 'p', text: 'FIX: read the exact error text in the Messages panel - each of the three cases has its own, specific message. A file with too new a version needs a newer editor build; a wrong format is not a file from this program at all.' },
    ],
  },
  // ==================== CHAPTER 12 - KEYBOARD SHORTCUTS ====================
  'shortcuts-all': {
    pl: [
      { kind: 'p', text: 'Ponizsza lista jest wyciagnieta wprost z obslugi klawiatury w kodzie (`Canvas.tsx`, `App.tsx`, `HelpWindow.tsx`) - nie z pamieci. Jesli jakis skrot wydaje sie oczywisty, a nie jest tu wymieniony (np. Ctrl+Z/Ctrl+Y dla cofania/ponawiania), to znaczy, ze w tej wersji edytora dziala WYLACZNIE z menu Edit, nie z klawiatury - sprawdzone wprost w kodzie, nie zalozone.' },
      { kind: 'heading', text: 'Zaznaczanie' },
      { kind: 'table', headers: ['Skrot', 'Dzialanie', 'Gdzie'], rows: [
        ['Ctrl/Cmd+A', 'Zaznacz wszystko na biezacym ekranie', 'Schemat'],
        ['Shift+klik', 'Dodaj/usun z zaznaczenia', 'Schemat'],
        ['Escape', 'Wyczysc zaznaczenie (jesli nic innego nie jest w toku)', 'Schemat'],
      ] },
      { kind: 'heading', text: 'Edycja' },
      { kind: 'table', headers: ['Skrot', 'Dzialanie', 'Gdzie'], rows: [
        ['Ctrl/Cmd+C', 'Kopiuj zaznaczenie', 'Schemat'],
        ['Ctrl/Cmd+V', 'Wklej (przesuniete o jedno oczko)', 'Schemat'],
        ['Ctrl/Cmd+D', 'Powiel zaznaczenie w miejscu', 'Schemat'],
        ['Delete / Backspace', 'Usun zaznaczenie', 'Schemat'],
        ['Strzalki', 'Przesun zaznaczenie o jedno oczko (dziesiec z Shift)', 'Schemat'],
      ] },
      { kind: 'heading', text: 'Widok' },
      { kind: 'table', headers: ['Skrot', 'Dzialanie', 'Gdzie'], rows: [
        ['Spacja (przytrzymana)', 'Tryb przewijania (reka)', 'Schemat'],
        ['Ctrl/Cmd+0', 'Przywroc powiekszenie 100%', 'Schemat'],
        ['Ctrl/Cmd+9', 'Dopasuj widok do calej zawartosci', 'Schemat'],
      ] },
      { kind: 'heading', text: 'Narzedzia rysowania' },
      { kind: 'table', headers: ['Skrot', 'Dzialanie', 'Gdzie'], rows: [
        ['1 / 2 / 3', 'Wybierz osrodek nowego przewodu (prad/woda/wentylacja)', 'Schemat'],
        ['Enter', 'Zakoncz rysowanie przewodu', 'Schemat'],
        ['Backspace (w trakcie rysowania)', 'Cofnij ostatni punkt przewodu', 'Schemat'],
        ['Alt+klik na przewodzie', 'Wstaw punkt zalamania', 'Schemat'],
        ['Alt (przytrzymany, podczas przeciagania)', 'Chwilowo wylacz przyciaganie do siatki', 'Schemat'],
      ] },
      { kind: 'heading', text: 'Pomoc' },
      { kind: 'table', headers: ['Skrot', 'Dzialanie'], rows: [
        ['F1', 'Otworz pomoc na rozdziale zwiazanym z biezacym zaznaczeniem'],
        ['Escape', 'Zamknij okno pomocy'],
      ] },
    ],
    en: [
      { kind: 'p', text: 'The list below is pulled directly from the keyboard handling in the code (`Canvas.tsx`, `App.tsx`, `HelpWindow.tsx`) - not from memory. If a shortcut seems obvious and is not listed here (e.g. Ctrl+Z/Ctrl+Y for undo/redo), that means this editor version only offers it from the Edit menu, not the keyboard - checked directly in the code, not assumed.' },
      { kind: 'heading', text: 'Selection' },
      { kind: 'table', headers: ['Shortcut', 'Action', 'Where'], rows: [
        ['Ctrl/Cmd+A', 'Select everything on the current screen', 'Schematic'],
        ['Shift+click', 'Add/remove from the selection', 'Schematic'],
        ['Escape', 'Clear selection (if nothing else is in progress)', 'Schematic'],
      ] },
      { kind: 'heading', text: 'Editing' },
      { kind: 'table', headers: ['Shortcut', 'Action', 'Where'], rows: [
        ['Ctrl/Cmd+C', 'Copy the selection', 'Schematic'],
        ['Ctrl/Cmd+V', 'Paste (offset by one grid cell)', 'Schematic'],
        ['Ctrl/Cmd+D', 'Duplicate the selection in place', 'Schematic'],
        ['Delete / Backspace', 'Delete the selection', 'Schematic'],
        ['Arrow keys', 'Move the selection by one grid cell (ten with Shift)', 'Schematic'],
      ] },
      { kind: 'heading', text: 'View' },
      { kind: 'table', headers: ['Shortcut', 'Action', 'Where'], rows: [
        ['Space (held)', 'Pan mode (hand cursor)', 'Schematic'],
        ['Ctrl/Cmd+0', 'Reset zoom to 100%', 'Schematic'],
        ['Ctrl/Cmd+9', 'Fit the view to all content', 'Schematic'],
      ] },
      { kind: 'heading', text: 'Drawing tools' },
      { kind: 'table', headers: ['Shortcut', 'Action', 'Where'], rows: [
        ['1 / 2 / 3', 'Pick a new wire\'s medium (electrical/water/ventilation)', 'Schematic'],
        ['Enter', 'Finish drawing a wire', 'Schematic'],
        ['Backspace (while drawing)', 'Undo the last wire point', 'Schematic'],
        ['Alt+click on a wire', 'Insert a bend point', 'Schematic'],
        ['Alt (held, while dragging)', 'Temporarily disable snap-to-grid', 'Schematic'],
      ] },
      { kind: 'heading', text: 'Help' },
      { kind: 'table', headers: ['Shortcut', 'Action'], rows: [
        ['F1', 'Open help on the topic related to the current selection'],
        ['Escape', 'Close the help window'],
      ] },
    ],
  },
};
