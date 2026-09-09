// feat/help-system commit 4 - full content for chapters 5-7, Polish and
// English. Checked against NetResolver.ts, WireDrawing.ts, Terminals.ts,
// SymbolRegistry.ts (registry/scada.ts), MeterElement.ts/MeterResolver.ts,
// SignalPanelElement.ts/SignalPanelResolver.ts and FrameElement.ts.

import type { HelpContentMap } from './HelpContentRegistry';

export const HELP_CONTENT_DRAWING: HelpContentMap = {
  // ==================== CHAPTER 5 - SCHEMATIC SCREEN ====================
  'sch-node-model': {
    pl: [
      { kind: 'p', text: 'Przewod na schemacie to swobodnie rysowana lamana ortogonalna (tylko odcinki poziome i pionowe) - NIE para portow. Dwa przewody, albo przewod i zacisk symbolu, naleza do TEJ SAMEJ sieci elektrycznej/wodnej/wentylacyjnej wylacznie dlatego, ze dotykaja sie GEOMETRYCZNIE - w tym samym punkcie siatki.' },
      { kind: 'p', text: 'Dotkniecie moze byc na SRODKU odcinka innego przewodu, nie tylko na jego koncu - to wlasnie umozliwia szyne zbiorcza ([[sch-wire-style|5.4]]): kazdy przewod stykajacy sie z dowolnym punktem jej dlugosci nalezy do tej samej sieci.' },
      { kind: 'p', text: 'Brak portow upraszcza edycje: mozna przesunac zacisk symbolu (zmieniajac jego rozmiar - [[sym-terminals|6.2]]) albo przeciagnac wezel przewodu, a polaczenie ISTNIEJE dopoki punkty faktycznie sie stykaja, bez zadnego osobnego "polaczenia" do naprawienia albo utracenia. Siec jest przeliczana na nowo z samej geometrii (`resolveNets` w `NetResolver.ts`), nigdy nie jest zapisana wprost w pliku projektu.' },
    ],
    en: [
      { kind: 'p', text: 'A schematic wire is a freely drawn orthogonal polyline (horizontal and vertical segments only) - NOT a pair of ports. Two wires, or a wire and a symbol terminal, belong to the SAME electrical/water/ventilation net purely because they touch GEOMETRICALLY - at the same grid point.' },
      { kind: 'p', text: 'A touch can be at the MIDDLE of another wire\'s segment, not only at its end - that is exactly what makes a busbar work ([[sch-wire-style|5.4]]): every wire touching any point along its length belongs to the same net.' },
      { kind: 'p', text: 'Having no ports simplifies editing: a symbol\'s terminal can move (by resizing it - [[sym-terminals|6.2]]) or a wire\'s node can be dragged, and the connection EXISTS as long as the points actually touch, with no separate "link" to repair or lose. The net is recomputed from geometry alone (`resolveNets` in `NetResolver.ts`), never stored explicitly in the project file.' },
    ],
  },
  'sch-drawing-wire': {
    pl: [
      { kind: 'p', text: 'Krok po kroku: wybierz osrodek (klawisze `1`/`2`/`3` albo przelacznik w toolbarze - [[sch-media|5.3]]), kliknij punkt startowy (najlepiej na zacisku symbolu), kliknij kolejne punkty, aby dodac zalamania, a Enter konczy rysowanie. Escape anuluje caly rysowany aktualnie przewod.' },
      { kind: 'p', text: 'Kazdy ruch myszy po skosie jest automatycznie zamieniany na dwa odcinki pod katem prostym (najpierw poziomo, potem pionowo) - nigdy nie powstaje odcinek ukosny. Backspace w trakcie rysowania cofa ostatnio dodany punkt (zalamanie), nie caly przewod.' },
      { kind: 'p', text: 'Na juz narysowanym przewodzie: Alt+klik na jego odcinku wstawia nowy punkt zalamania dokladnie w najblizszym miejscu na tym odcinku; przeciagniecie istniejacego punktu przewodu automatycznie dostawia potrzebne zalamania po obu stronach, zeby caly przewod pozostal ortogonalny.' },
    ],
    en: [
      { kind: 'p', text: 'Step by step: pick a medium (keys `1`/`2`/`3`, or the toolbar toggle - [[sch-media|5.3]]), click a starting point (ideally on a symbol\'s terminal), click further points to add bends, and Enter finishes the wire. Escape cancels the wire currently being drawn.' },
      { kind: 'p', text: 'Any diagonal mouse movement is automatically turned into two right-angle segments (horizontal first, then vertical) - a diagonal segment is never created. Backspace while drawing undoes the last point added (one bend), not the whole wire.' },
      { kind: 'p', text: 'On an already-finished wire: Alt+click on one of its segments inserts a new bend exactly at the nearest point on that segment; dragging an existing wire point automatically inserts whatever bends are needed on either side so the whole wire stays orthogonal.' },
    ],
  },
  'sch-media': {
    pl: [
      { kind: 'p', text: 'Kazdy przewod nalezy do jednego z trzech osrodkow: ELECTRICAL (prad), WATER (woda), VENTILATION (wentylacja). Wybor osrodka NOWEGO przewodu ustawia sie z gory (klawisze `1`/`2`/`3` albo przelacznik w toolbarze) - kazdy narysowany od tej pory przewod dziedziczy ten wybor, az do zmiany. Osrodek juz narysowanego przewodu mozna nadal zmienic pozniej we Properties.' },
      { kind: 'p', text: 'Siec, ktora dotyka zaciskow z wiecej niz jednego osrodka naraz, jest bledem walidacji (`MIXED_MEDIUM` w `NetResolver.ts`) - dotyczy to kazdej pary z tych trzech, nie tylko prad-woda: prad spiety z wentylacja jest tak samo bledny jak prad spiety z woda.' },
    ],
    en: [
      { kind: 'p', text: 'Every wire belongs to one of three media: ELECTRICAL, WATER, VENTILATION. A NEW wire\'s medium is chosen up front (keys `1`/`2`/`3`, or the toolbar toggle) - every wire drawn from then on inherits that choice until it is changed again. An already-drawn wire\'s medium can still be changed afterward in Properties.' },
      { kind: 'p', text: 'A net touching terminals of more than one medium at once is a validation error (`MIXED_MEDIUM` in `NetResolver.ts`) - this applies to any pair of the three, not just power-water: power tied to ventilation is just as invalid as power tied to water.' },
    ],
  },
  'sch-wire-style': {
    pl: [
      { kind: 'p', text: 'Kazdy przewod ma jeden z dwoch stylow: NORMAL (zwykly) albo BUS (szyna zbiorcza/rozdzielacz). Szyna NIE JEST osobnym symbolem ani osobnym mechanizmem sieciowym - to ten sam przewod, narysowany grubiej, zeby wizualnie zaznaczyc, ze jest przeznaczony do podlaczania wielu odbiorow na calej dlugosci. Rozdzielacz wodny to dokladnie to samo, tylko w osrodku WATER.' },
      { kind: 'p', text: 'Mechanizm "przylaczenia sie w dowolnym punkcie dlugosci" nie jest w ogole ograniczony do stylu BUS - kazdy przewod, niezaleznie od stylu, laczy sie z innym przewodem dotykajac go w SRODKU jego odcinka, nie tylko na koncu (patrz [[sch-node-model|5.1]]). Styl BUS jest wylacznie wizualna zapowiedzia tej intencji, nie warunkiem jej dzialania.' },
      { kind: 'p', text: 'Styl NOWEGO przewodu wybiera sie z gory w toolbarze (obok wyboru osrodka), tak samo jak medium - juz narysowany przewod mozna przelaczyc pozniej we Properties.' },
    ],
    en: [
      { kind: 'p', text: 'Every wire has one of two styles: NORMAL or BUS (busbar/manifold). A busbar is NOT a separate symbol or a separate networking mechanism - it is the same wire, drawn thicker, to visually flag that it is meant to have many loads tapped along its whole length. A water manifold is exactly the same thing, just in the WATER medium.' },
      { kind: 'p', text: 'The "tap in at any point along the length" mechanism is not actually limited to the BUS style at all - any wire, regardless of style, joins another wire by touching it in the MIDDLE of a segment, not only at an end (see [[sch-node-model|5.1]]). The BUS style is purely a visual signal of that intent, not a condition for it working.' },
      { kind: 'p', text: 'A NEW wire\'s style is chosen up front in the toolbar (next to the medium choice), the same way medium is - an already-drawn wire can still be switched afterward in Properties.' },
    ],
  },
  'sch-junction-dot': {
    pl: [
      { kind: 'p', text: 'Kropka wezlowa pojawia sie w kazdym punkcie siatki, w ktorym spotykaja sie TRZY LUB WIECEJ galezi - trzy lub wiecej odcinkow przewodow, albo dwa odcinki i zacisk symbolu (`getJunctionPoints` w `NetResolver.ts`).' },
      { kind: 'p', text: 'Zwykle zagiecie tego samego przewodu (dwa jego wlasne odcinki spotykajace sie w jednym punkcie) NIE jest junction - to tylko naroznik, liczy sie jako dwie galezie, nie trzy. Punkt w SRODKU dlugosci jednego odcinka (np. odczep od szyny - [[sch-wire-style|5.4]]) liczy sie jako DWIE galezie tego jednego odcinka (bo dzieli go koncepcyjnie na dwa), wiec odczep + ten punkt srodkowy dają razem trzy - i tam kropka sie pojawia.' },
    ],
    en: [
      { kind: 'p', text: 'A junction dot appears at every grid point where THREE OR MORE branches meet - three or more wire segments, or two segments plus a symbol terminal (`getJunctionPoints` in `NetResolver.ts`).' },
      { kind: 'p', text: 'An ordinary bend in the same wire (its own two segments meeting at one point) is NOT a junction - it is just a corner, counting as two branches, not three. A point in the MIDDLE of one segment\'s length (e.g. a tap off a busbar - [[sch-wire-style|5.4]]) counts as TWO branches of that one segment (because it conceptually splits it in two), so a tap plus that midpoint together make three - and that is where the dot appears.' },
    ],
  },
  'sch-net-validation': {
    pl: [
      { kind: 'p', text: 'Walidacja sieci dziala na juz wyliczonych sieciach (`validateNets` w `NetResolver.ts`), nie na pojedynczych przewodach:' },
      { kind: 'table', headers: ['Kod', 'Waga', 'Znaczenie'], rows: [
        ['MIXED_MEDIUM', 'blad', 'Siec dotyka zaciskow z wiecej niz jednego osrodka - patrz [[sch-media|5.3]].'],
        ['DANGLING_NET', 'ostrzezenie', 'Przewod nie dotyka zadnego zacisku - "przewod donikad".'],
        ['MULTIPLE_SOURCES', 'ostrzezenie', 'Dwa lub wiecej punkty graniczne SOURCE spiete w jedna siec - dwa zasilania razem.'],
      ] },
      { kind: 'p', text: 'To rozne od walidacji ksztaltu pojedynczego przewodu (np. zakaz odcinka po skosie) - ta druga jest sprawdzana na poziomie schematu jako calosci przy zapisie (`validateProjectSchema` w `ProjectSchema.ts`), nie na poziomie sieci.' },
    ],
    en: [
      { kind: 'p', text: 'Net validation runs on already-resolved nets (`validateNets` in `NetResolver.ts`), not on individual wires:' },
      { kind: 'table', headers: ['Code', 'Severity', 'Meaning'], rows: [
        ['MIXED_MEDIUM', 'error', 'A net touches terminals of more than one medium - see [[sch-media|5.3]].'],
        ['DANGLING_NET', 'warning', 'A wire touches no terminal at all - "a wire to nowhere".'],
        ['MULTIPLE_SOURCES', 'warning', 'Two or more SOURCE boundary points tied into one net - two supplies joined together.'],
      ] },
      { kind: 'p', text: 'This is different from validating a single wire\'s own shape (e.g. no diagonal segments) - that is checked at the whole-schematic level on save (`validateProjectSchema` in `ProjectSchema.ts`), not at the net level.' },
    ],
  },
  'sch-boundary-point': {
    pl: [
      { kind: 'p', text: 'Punkt graniczny reprezentuje miejsce, w ktorym instalacja na tym ekranie laczy sie ze swiatem zewnetrznym: przylacze energetyczne, studnia, punkt zrzutu. To jedyny symbol z polem kierunku: Boundary Direction, SOURCE (zrodlo) albo SINK (odplyw), plus Boundary Medium (ELECTRICAL/WATER/VENTILATION).' },
      { kind: 'p', text: 'Dwa punkty graniczne SOURCE spiete w jedna siec sa ostrzezeniem (`MULTIPLE_SOURCES`, [[sch-net-validation|5.6]]) - dwa niezalezne zasilania podpiete razem to realny problem instalacyjny (np. rownolegla praca dwoch zrodel bez synchronizacji), ktory warto zauwazyc juz na etapie projektowania ekranu.' },
      { kind: 'p', text: 'Etykieta i podetykieta punktu granicznego to designation/description tego obiektu (nie osobne pola), a jego jedyny zacisk lezy po stronie wskazanej polem Boundary Port Side (gora/dol/lewo/prawo) - w przeciwienstwie do kazdego innego symbolu, ktorego zaciski maja stale pozycje z rejestru ([[sym-terminals|6.2]]), ten jeden ma pozycje zacisku wybierana per instancja.' },
    ],
    en: [
      { kind: 'p', text: 'A boundary point represents the spot where the installation on this screen meets the outside world: a utility connection, a well, a discharge point. It is the only symbol with a direction field: Boundary Direction, SOURCE or SINK, plus Boundary Medium (ELECTRICAL/WATER/VENTILATION).' },
      { kind: 'p', text: 'Two SOURCE boundary points tied into one net is a warning (`MULTIPLE_SOURCES`, [[sch-net-validation|5.6]]) - two independent supplies joined together is a real installation concern (e.g. two sources running in parallel with no synchronization), worth catching at the screen-design stage.' },
      { kind: 'p', text: 'A boundary point\'s label and sub-label are this object\'s own designation/description (not separate fields), and its single terminal sits on the side named by its Boundary Port Side field (top/bottom/left/right) - unlike every other symbol, whose terminals sit at fixed positions from the registry ([[sym-terminals|6.2]]), this one\'s terminal side is chosen per instance.' },
    ],
  },

  // ==================== CHAPTER 6 - SYMBOLS ====================
  'sym-library': {
    pl: [
      { kind: 'p', text: 'Biblioteka symboli (panel Object Library) jest podzielona na kategorie: Electrical, Water, HVAC, Instrumentation, SCADA i inne - kazdy symbol nalezy do jednej. Przeciagniecie symbolu z biblioteki na plotno tworzy nowy obiekt na schemacie.' },
      { kind: 'p', text: 'Kazdy symbol ma swoja definicje (typ, etykiete, domyslny rozmiar, dopuszczalne stany, zaciski) w rejestrze symboli - jedynym miejscu, ktore decyduje, co dany typ symbolu w ogole potrafi. Kilka symboli moze byc oznaczonych jako ukryte z biblioteki (nadal poprawnie dzialaja, jesli juz istnieja w otwartym projekcie), co nie zmienia niczego w tym, jak sie ich uzywa - tylko czy pojawiaja sie w panelu do przeciagniecia.' },
    ],
    en: [
      { kind: 'p', text: 'The symbol library (the Object Library panel) is split into categories: Electrical, Water, HVAC, Instrumentation, SCADA and others - every symbol belongs to exactly one. Dragging a symbol from the library onto the canvas creates a new schematic object.' },
      { kind: 'p', text: 'Every symbol has its own definition (type, label, default size, allowed states, terminals) in the symbol registry - the one place that decides what a given symbol type can do at all. A few symbols are flagged as hidden from the library (they still work correctly if they already exist in an open project), which changes nothing about how they are used - only whether they show up in the panel to be dragged.' },
    ],
  },
  'sym-terminals': {
    pl: [
      { kind: 'p', text: 'Kazdy zacisk symbolu lezy ZAWSZE dokladnie na srodku jednej z czterech krawedzi (gora, dol, lewo, prawo) obiektu - rejestr symbolu deklaruje TYLKO, ktora to krawedz, nigdy surowej pozycji x/y. Faktyczna pozycja jest wyliczana z aktualnej szerokosci i wysokosci obiektu (`getObjectTerminals` w `Terminals.ts`) w momencie, gdy jest potrzebna, nie zapisana na stale.' },
      { kind: 'p', text: 'Konsekwencja praktyczna: gdy symbol jest zmieniony rozmiarem (np. zawor rozciagniety, zeby wpasowac sie w istniejacy uklad rury), jego zacisk PODAZA za nowym srodkiem krawedzi automatycznie - nie zostaje przypiety do miejsca, w ktorym byl przy domyslnym rozmiarze. Wyjatkiem jest punkt graniczny ([[sch-boundary-point|5.7]]), ktorego jedyny zacisk zalezy od pola Boundary Port Side, a nie od rozmiaru.' },
    ],
    en: [
      { kind: 'p', text: 'A symbol\'s terminal always sits exactly at the middle of one of the four edges (top, bottom, left, right) of the object - the symbol registry only ever declares WHICH edge, never a raw x/y position. The actual position is computed from the object\'s current width and height (`getObjectTerminals` in `Terminals.ts`) whenever it is needed, never stored fixed.' },
      { kind: 'p', text: 'Practical consequence: when a symbol is resized (e.g. a valve stretched to fit an existing pipe run), its terminal FOLLOWS the new edge midpoint automatically - it does not stay pinned where it was at the default size. The exception is the boundary point ([[sch-boundary-point|5.7]]), whose single terminal depends on its Boundary Port Side field, not on its size.' },
    ],
  },
  'sym-states-preview': {
    pl: [
      { kind: 'p', text: 'Kazdy typ symbolu deklaruje w rejestrze wlasna liste dopuszczalnych stanow (`allowedStates`) i stan domyslny. Przyklad: dioda sygnalizacyjna ma ON/OFF/QUALITY, miernik (SCADA, statyczny symbol - patrz [[elem-meter|7.1]]) nie ma zadnego stanu wlasnego.' },
      { kind: 'p', text: 'Poniewaz edytor nie ma zywych danych, aktualnie WYSWIETLANY stan pochodzi z pola `editor.preview_state` na obiekcie - to reczne ustawienie w Properties, sluzace wylacznie do zobaczenia, jak symbol wyglada w danym stanie podczas projektowania, nigdy odczyt z prawdziwego sprzetu.' },
    ],
    en: [
      { kind: 'p', text: 'Every symbol type declares its own list of allowed states (`allowedStates`) and a default state in the registry. Example: the indicator diode has ON/OFF/QUALITY; the meter (SCADA, the static symbol - see [[elem-meter|7.1]]) has no state of its own at all.' },
      { kind: 'p', text: 'Since the editor has no live data, the state currently DISPLAYED comes from the object\'s own `editor.preview_state` field - a manual setting in Properties, used purely to see how the symbol looks in a given state while designing, never a reading from real hardware.' },
    ],
  },
  'sym-device-binding': {
    pl: [
      { kind: 'p', text: 'Kazdy symbol (poza czysta grafika i liniami) ma we Properties pole Aparat - rozwijana liste wszystkich aparatow projektu. Symbol BEZ przypisanego aparatu jest w pelni poprawnym stanem - to czysta grafika bez zadnego zwiazku z lista aparatow.' },
      { kind: 'p', text: 'Wybranie aparatu, gdy pole Oznaczenie symbolu jest puste, automatycznie wypelnia je oznaczeniem tego aparatu - ale TYLKO jednorazowo, w momencie wyboru, i TYLKO gdy bylo puste. Zmiana oznaczenia aparatu pozniej nie zmienia juz wpisanego oznaczenia symbolu (a wpisanie czegos innego recznie do Oznaczenia nigdy nie jest nadpisywane przez ponowny wybor aparatu).' },
      { kind: 'p', text: 'Ten sam aparat przypisany do wielu roznych symboli jest poprawny i nie zglasza zadnego bledu - patrz [[dev-why-not-in-screen|4.1]]. Symbol wskazujacy na identyfikator aparatu, ktory nie istnieje juz w rejestrze (np. zostal usuniety), nadal renderuje sie normalnie, ale dostaje przerywana czerwona obwodke i trafia do panelu Messages jako ostrzezenie - patrz [[edit-messages-panel|9.7]] i [[ts-symbol-red-outline|rozdzial 11]].' },
    ],
    en: [
      { kind: 'p', text: 'Every symbol (except pure graphics and lines) has an Aparat field in Properties - a dropdown of every device in the project. A symbol with NO device assigned is a fully valid state - it is pure graphics with no relation to the device list at all.' },
      { kind: 'p', text: 'Choosing a device while the symbol\'s own Designation field is empty auto-fills it with that device\'s designation - but ONLY once, at the moment of choosing, and ONLY when it was empty. Changing the device\'s own designation afterward does not change the symbol\'s already-filled designation (and typing something else into Designation by hand is never overwritten by picking a device again).' },
      { kind: 'p', text: 'The same device assigned to many different symbols is valid and reports no error - see [[dev-why-not-in-screen|4.1]]. A symbol pointing at a device id that no longer exists in the registry (e.g. it was deleted) still renders completely normally, but gets a dashed red outline and is reported to the Messages panel as a warning - see [[edit-messages-panel|9.7]] and [[ts-symbol-red-outline|chapter 11]].' },
    ],
  },
  'sym-labels': {
    pl: [
      { kind: 'p', text: 'Etykieta symbolu ma dwie linie: oznaczenie (pogrubione, pokazywane tylko gdy niepuste) i nazwe (druga linia, tylko gdy wlaczona przelacznikiem Show Name i niepusta). Etykieta jest rysowana WYLACZNIE z danych wpisanych przez uzytkownika - nigdy z zastepczej wartosci typu identyfikator obiektu czy typ symbolu. Symbol bez oznaczenia i bez wlaczonej nazwy po prostu nie ma etykiety wcale.' },
      { kind: 'p', text: 'Etykiete mozna przeciagnac osobno od symbolu (chwytajac ja bezposrednio) - jej pozycja wzgledem symbolu jest wtedy zapamietywana. Dwuklik na etykiecie otwiera edycje oznaczenia wprost na miejscu; Enter zatwierdza, Escape anuluje bez zapisania zmiany.' },
    ],
    en: [
      { kind: 'p', text: 'A symbol\'s label has two lines: the designation (bold, shown only when non-empty) and the name (a second line, shown only when the Show Name toggle is on and it is non-empty). The label is drawn EXCLUSIVELY from user-entered data - never from a placeholder like the object\'s id or its symbol type. A symbol with no designation and no name toggled on simply has no label at all.' },
      { kind: 'p', text: 'A label can be dragged separately from its symbol (grabbing it directly) - its position relative to the symbol is then remembered. Double-clicking the label opens its designation for editing right there; Enter commits it, Escape cancels without saving the change.' },
    ],
  },

  // ==================== CHAPTER 7 - SCREEN ELEMENTS ====================
  'elem-meter': {
    pl: [
      { kind: 'p', text: 'UWAGA: sa DWA rozne "mierniki" w tym edytorze. Statyczny symbol SCADA "Meter (SCADA)" z biblioteki to zwykla grafika bez wierszy i bez wlasnego stanu - jak kazdy inny symbol. Ten rozdzial opisuje DRUGI, dynamiczny element Miernik (przycisk w toolbarze), zbudowany z wierszy.' },
      { kind: 'p', text: 'Miernik ma dowolna liczbe wierszy; kazdy wiersz albo wskazuje na aparat MEASURED (jednostka, format i wartosc podgladu - srodek zakresu - pochodza ZAWSZE z aparatu, nigdy nie sa kopiowane na wiersz), albo jest wierszem recznym z wlasna wartoscia i jednostka wpisana wprost. Wysokosc miernika jest ZAWSZE wyliczana z liczby wierszy, obecnosci tytulu i rozmiaru czcionki - nie ma pola wysokosci do recznego ustawienia.' },
      { kind: 'p', text: 'Kreator wyboru pomiarow (przycisk Kreator...) pokazuje WYLACZNIE aparaty o zachowaniu MEASURED, pogrupowane po jednostce - jesli lista jest pusta, w projekcie nie ma jeszcze zadnego aparatu MEASURED (patrz [[dev-measured|4.6]] i [[ts-meter-wizard-empty|rozdzial 11]]).' },
      { kind: 'p', text: 'Wiersz wskazujacy na aparat, ktory nie istnieje albo nie ma zachowania MEASURED, jest oznaczany kolorem MISSING zamiast rzucac wyjatek.' },
    ],
    en: [
      { kind: 'p', text: 'NOTE: there are TWO different "meters" in this editor. The static SCADA symbol "Meter (SCADA)" from the library is plain graphics with no rows and no state of its own - like any other symbol. This chapter covers the SECOND, dynamic Meter element (a toolbar button), built from rows.' },
      { kind: 'p', text: 'A meter has any number of rows; each row either points at a MEASURED device (unit, format and the preview value - the middle of the range - always come FROM the device, never copied onto the row), or is a manual row with its own value and unit typed directly. A meter\'s height is ALWAYS computed from its row count, whether it has a title, and its font size - there is no height field to set by hand.' },
      { kind: 'p', text: 'The measurement-picker wizard (the Kreator... button) shows ONLY MEASURED devices, grouped by unit - if the list is empty, the project has no MEASURED device yet (see [[dev-measured|4.6]] and [[ts-meter-wizard-empty|chapter 11]]).' },
      { kind: 'p', text: 'A row pointing at a device that does not exist, or that is not itself MEASURED, is marked with the MISSING color instead of throwing an exception.' },
    ],
  },
  'elem-signal-panel': {
    pl: [
      { kind: 'p', text: 'Panel sygnalizacyjny to ten sam mechanizm co miernik ([[elem-meter|7.1]]), ale kazdy wiersz konczy sie DIODA dwustanowa zamiast pola wartosci. Wiersz albo wskazuje na aparat, albo jest wierszem recznym z wlasnym stanem diody ustawionym wprost (ON/OFF/QUALITY).' },
      { kind: 'p', text: 'Kreator panelu (przycisk Kreator...) pokazuje aparaty SIGNAL i SWITCHED, pogrupowane po LOKALIZACJI (nie po jednostce, jak kreator miernika) - MEASURED nigdy sie tu nie pojawia, bo nie ma pojecia "zamkniety/otwarty" do zasygnalizowania diodą.' },
      { kind: 'p', text: 'Wiersz wskazujacy na prawidlowy aparat SIGNAL/SWITCHED zawsze pokazuje diode w stanie ON w podgladzie - to reczny podglad projektowy (edytor nie ma zywych danych), nie odczyt rzeczywistego stanu stykow. Wiersz wskazujacy na aparat, ktory nie istnieje albo ma inne zachowanie (np. MEASURED), pokazuje diode QUALITY zamiast rzucac wyjatek.' },
    ],
    en: [
      { kind: 'p', text: 'A signal panel is the same mechanism as the meter ([[elem-meter|7.1]]), except every row ends in a two-state DIODE instead of a value field. A row either points at a device, or is a manual row with its own diode state set directly (ON/OFF/QUALITY).' },
      { kind: 'p', text: 'The panel wizard shows SIGNAL and SWITCHED devices, grouped by LOCATION (not by unit, unlike the meter wizard) - MEASURED never appears here, since it has no "closed/open" notion for a diode to signal.' },
      { kind: 'p', text: 'A row pointing at a valid SIGNAL/SWITCHED device always previews its diode as ON - a manual design-time preview (the editor has no live data), not a reading of a real contact\'s state. A row pointing at a device that does not exist, or that has a different behavior (e.g. MEASURED), shows the QUALITY diode instead of throwing an exception.' },
    ],
  },
  'elem-frame-building': {
    pl: [
      { kind: 'p', text: 'Ramka to czysta grafika ilustrujaca szafe, pomieszczenie albo strefe - bez zaciskow, bez polaczen, bez stanu i bez pola Aparat. Ma dwa warianty: plain (zwykla ramka) i building (budynek), plus opcjonalny tytul umieszczony w lewym gornym rogu albo wysrodkowany u gory.' },
      { kind: 'p', text: 'Rysuje sie ja przeciagnieciem prostokata, tak jak `graphics.rectangle` - z jednym ograniczeniem: minimalny rozmiar to dwa oczka siatki w kazdym wymiarze; przeciagniecie mniejszego prostokata i tak tworzy ramke o rozmiarze minimalnym, nie zerowym.' },
    ],
    en: [
      { kind: 'p', text: 'A frame is pure graphics illustrating a cabinet, a room or a zone - no terminals, no connections, no state, and no Aparat field. It has two variants: plain and building, plus an optional title placed at the top-left or centered along the top.' },
      { kind: 'p', text: 'It is drawn by dragging a rectangle, the same way `graphics.rectangle` is - with one constraint: the minimum size is two grid cells in each direction; dragging a smaller rectangle still produces a minimum-size frame, never a zero-size one.' },
    ],
  },
  'elem-boundary-point': {
    pl: [
      { kind: 'p', text: 'Jako ELEMENT EKRANU (w odroznieniu od koncepcji sieciowej opisanej w [[sch-boundary-point|5.7]]): punkt graniczny jest symbolem jak kazdy inny w bibliotece (kategoria SCADA), z tym ze jego rozmiar dopasowuje sie do dlugosci wpisanej etykiety/podetykiety (ta sama logika co ramka z tytulem), a nie jest stalym prostokatem.' },
      { kind: 'p', text: 'Ustawia sie na nim trzy pola specyficzne wylacznie dla tego symbolu: Boundary Direction (SOURCE/SINK), Boundary Medium (ELECTRICAL/WATER/VENTILATION) i Boundary Port Side (ktora krawedz ma zacisk) - zadne inne pole Properties (np. Bindings) nie ma tu zadnego dodatkowego znaczenia ponad to, co maja u kazdego innego symbolu.' },
    ],
    en: [
      { kind: 'p', text: 'As a SCREEN ELEMENT (as distinct from the net-level concept covered in [[sch-boundary-point|5.7]]): a boundary point is a symbol like any other in the library (SCADA category), except its size fits the length of its own label/sub-label text (the same logic a titled frame uses), rather than being a fixed rectangle.' },
      { kind: 'p', text: 'It carries three fields specific only to this symbol: Boundary Direction (SOURCE/SINK), Boundary Medium (ELECTRICAL/WATER/VENTILATION) and Boundary Port Side (which edge carries the terminal) - no other Properties field (e.g. Bindings) means anything extra here beyond what it means on every other symbol.' },
    ],
  },
  'elem-indicator-diode': {
    pl: [
      { kind: 'p', text: 'Dioda sygnalizacyjna to symbol z trzema dopuszczalnymi stanami: ON (swiecaca, zielony rdzen), OFF (ciemna, matowa) i QUALITY (zolta - uzywana m.in. do oznaczenia brakujacego/nieprawidlowego zrodla danych, np. w wierszu panelu sygnalizacyjnego wskazujacym na nieistniejacy aparat - [[elem-signal-panel|7.2]]).' },
      { kind: 'p', text: 'Kolor stanu ALARM (czerwony) jest osobnym, trzecim zestawem kolorow diody, uzywanym poza samym symbolem diody - w panelach i innych miejscach, gdzie trzeba zasygnalizowac stan alarmowy, niezaleznie od tego, czy dana instancja diody akurat jest w stanie ON/OFF/QUALITY.' },
      { kind: 'p', text: 'Rozmiar promienia diody ma dwie stale wartosci z motywu: mniejsza przy aparatach na schemacie, wieksza w panelach sygnalizacyjnych i panelach stanu - nigdy wartosc wpisana lokalnie w komponencie.' },
    ],
    en: [
      { kind: 'p', text: 'The indicator diode is a symbol with three allowed states: ON (lit, a green core), OFF (dark, matte) and QUALITY (yellow - used, among other things, to flag a missing/invalid data source, e.g. a signal panel row pointing at a device that no longer exists - [[elem-signal-panel|7.2]]).' },
      { kind: 'p', text: 'The ALARM state color (red) is a separate, third diode color set, used beyond the diode symbol itself - in panels and other places that need to signal an alarm condition, independent of whether that particular diode instance is currently ON/OFF/QUALITY.' },
      { kind: 'p', text: 'The diode\'s radius has two fixed theme values: a smaller one for diodes on schematic symbols, a larger one in signal and status panels - never a value typed locally in a component.' },
    ],
  },
};
