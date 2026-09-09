// feat/help-system commit 2 - the table of contents: every chapter and
// topic id/title this help system will ever have, in Polish and English.
// Built here, in full, before any topic BODY exists - HelpContentRegistry.ts
// (also this commit) already handles a topic with no body gracefully (a
// short, honest placeholder, never a crash), which is exactly the state
// most topics are in until commits 3-5 fill their content in. The ids
// below never change once a content commit starts writing to them.
//
// chore/remove-isometric-plan-mode: chapter 8 (the isometric PLAN
// screen) has been removed in full, along with the mode itself - its
// own 6 topics are gone, not merely emptied. Chapters 9-13 deliberately
// keep their own existing ids/numbers unchanged rather than shifting
// down to fill the gap: every cross-reference elsewhere in this help
// embeds a chapter/topic NUMBER directly in its own label text (e.g.
// `[[file-contents|10.1]]`), and renumbering every one of those to
// match would be its own large, error-prone rewrite that this task
// never asked for - a numbering gap after a removed chapter is a
// normal, honest way to show it is gone, not a defect to paper over.

import type { HelpChapterMeta, HelpTopicMeta } from './HelpTypes';

export const HELP_TOC: HelpChapterMeta[] = [
  {
    id: 'ch1', title: { pl: '1. Wprowadzenie', en: '1. Introduction' },
    topics: [
      { id: 'intro-what', title: { pl: '1.1 Czym jest EPW-Synoptic-Editor', en: '1.1 What EPW-Synoptic-Editor Is' } },
      { id: 'intro-platform', title: { pl: '1.2 Miejsce w platformie EPW', en: '1.2 Place in the EPW Platform' } },
      { id: 'intro-principle', title: { pl: '1.3 Zasada nadrzedna: ekran informuje, sprzet chroni', en: '1.3 Governing Principle: the Screen Informs, the Hardware Protects' } },
      { id: 'intro-screens', title: { pl: '1.4 Rodzaj ekranu i pole kind', en: '1.4 Screen Kind and the kind Field' } },
    ],
  },
  {
    id: 'ch2', title: { pl: '2. Pierwsze kroki', en: '2. Getting Started' },
    topics: [
      { id: 'start-new-project', title: { pl: '2.1 Nowy projekt', en: '2.1 New Project' } },
      { id: 'start-order', title: { pl: '2.2 Kolejnosc pracy: najpierw rejestry, potem aparaty, potem ekran', en: '2.2 Working Order: Registries First, Then Devices, Then the Screen' } },
      { id: 'start-save-open', title: { pl: '2.3 Zapis i otwarcie projektu', en: '2.3 Saving and Opening a Project' } },
      { id: 'start-example', title: { pl: '2.4 Kompletny przyklad od zera', en: '2.4 A Complete Example From Scratch' } },
    ],
  },
  {
    id: 'ch3', title: { pl: '3. Rejestry projektu', en: '3. Project Registries' },
    topics: [
      { id: 'reg-locations', title: { pl: '3.1 Lokalizacje', en: '3.1 Locations' } },
      { id: 'reg-cards', title: { pl: '3.2 Karty wejsc i wyjsc', en: '3.2 I/O Cards' } },
      { id: 'reg-addressing', title: { pl: '3.3 Adresacja kanalow', en: '3.3 Channel Addressing' } },
      { id: 'reg-delete-protection', title: { pl: '3.4 Dlaczego usuniecie uzywanej lokalizacji albo karty jest zablokowane', en: '3.4 Why Deleting a Location or Card in Use Is Blocked' } },
    ],
  },
  {
    id: 'ch4', title: { pl: '4. Lista aparatow', en: '4. Device List' },
    topics: [
      { id: 'dev-why-not-in-screen', title: { pl: '4.1 Dlaczego konfiguracja aparatu nie siedzi w ekranie', en: '4.1 Why Device Configuration Does Not Live in the Screen' } },
      { id: 'dev-naming', title: { pl: '4.2 Konwencja nazewnicza', en: '4.2 Naming Convention' } },
      { id: 'dev-behavior-classification', title: { pl: '4.3 Klasyfikacja po zachowaniu, nie po rodzaju urzadzenia', en: '4.3 Classification by Behavior, Not by Device Kind' } },
      { id: 'dev-switched', title: { pl: '4.4 SWITCHED - sterowalne dwustanowe', en: '4.4 SWITCHED - Controllable Two-State Devices' } },
      { id: 'dev-signal', title: { pl: '4.5 SIGNAL - tylko sygnalizacyjne', en: '4.5 SIGNAL - Signalling-Only Devices' } },
      { id: 'dev-measured', title: { pl: '4.6 MEASURED - pomiarowe', en: '4.6 MEASURED - Measurement Devices' } },
      { id: 'dev-modulated', title: { pl: '4.7 MODULATED - sterowalne plynnie', en: '4.7 MODULATED - Continuously Controllable Devices' } },
      { id: 'dev-form-validation', title: { pl: '4.8 Formularz aparatu i walidacja na zywo', en: '4.8 The Device Form and Live Validation' } },
      { id: 'dev-signals-commands', title: { pl: '4.9 Sygnaly i komendy udostepniane logice sterowania', en: '4.9 Signals and Commands Exposed to Control Logic' } },
    ],
  },
  {
    id: 'ch5', title: { pl: '5. Ekran schematu', en: '5. Schematic Screen' },
    topics: [
      { id: 'sch-node-model', title: { pl: '5.1 Model wezlowy polaczen', en: '5.1 The Node-Based Connection Model' } },
      { id: 'sch-drawing-wire', title: { pl: '5.2 Rysowanie przewodu krok po kroku', en: '5.2 Drawing a Wire Step by Step' } },
      { id: 'sch-media', title: { pl: '5.3 Trzy osrodki: prad, woda, wentylacja', en: '5.3 Three Media: Electrical, Water, Ventilation' } },
      { id: 'sch-wire-style', title: { pl: '5.4 Styl przewodu: zwykly i szyna zbiorcza', en: '5.4 Wire Style: Normal and Busbar' } },
      { id: 'sch-junction-dot', title: { pl: '5.5 Kropka wezlowa - kiedy sie pojawia', en: '5.5 The Junction Dot - When It Appears' } },
      { id: 'sch-net-validation', title: { pl: '5.6 Walidacja sieci: niezgodnosc osrodkow, przewod donikad', en: '5.6 Net Validation: Mismatched Media, a Wire to Nowhere' } },
      { id: 'sch-boundary-point', title: { pl: '5.7 Punkt graniczny: zrodlo i odplyw instalacji', en: '5.7 Boundary Point: Source and Sink of the Installation' } },
    ],
  },
  {
    id: 'ch6', title: { pl: '6. Symbole', en: '6. Symbols' },
    topics: [
      { id: 'sym-library', title: { pl: '6.1 Biblioteka i kategorie', en: '6.1 Library and Categories' } },
      { id: 'sym-terminals', title: { pl: '6.2 Zaciski zawsze na srodku krawedzi', en: '6.2 Terminals Are Always at the Middle of an Edge' } },
      { id: 'sym-states-preview', title: { pl: '6.3 Stany symbolu i podglad w edytorze', en: '6.3 Symbol States and the Editor Preview' } },
      { id: 'sym-device-binding', title: { pl: '6.4 Powiazanie symbolu z aparatem', en: '6.4 Binding a Symbol to a Device' } },
      { id: 'sym-labels', title: { pl: '6.5 Etykiety: przesuwanie i edycja dwuklikiem', en: '6.5 Labels: Dragging and Double-Click Editing' } },
    ],
  },
  {
    id: 'ch7', title: { pl: '7. Elementy ekranu', en: '7. Screen Elements' },
    topics: [
      { id: 'elem-meter', title: { pl: '7.1 Miernik', en: '7.1 Meter' } },
      { id: 'elem-signal-panel', title: { pl: '7.2 Panel sygnalizacyjny', en: '7.2 Signal Panel' } },
      { id: 'elem-frame-building', title: { pl: '7.3 Ramka i budynek', en: '7.3 Frame and Building' } },
      { id: 'elem-boundary-point', title: { pl: '7.4 Punkt graniczny', en: '7.4 Boundary Point' } },
      { id: 'elem-indicator-diode', title: { pl: '7.5 Dioda sygnalizacyjna', en: '7.5 Indicator Diode' } },
    ],
  },
  {
    id: 'ch9', title: { pl: '9. Praca z edytorem', en: '9. Working With the Editor' },
    topics: [
      { id: 'edit-selection', title: { pl: '9.1 Zaznaczanie: klikniecie, ramka, Shift, Ctrl+A', en: '9.1 Selection: Click, Box, Shift, Ctrl+A' } },
      { id: 'edit-moving-snap', title: { pl: '9.2 Przesuwanie i przyciaganie do siatki', en: '9.2 Moving and Snapping to the Grid' } },
      { id: 'edit-copy-paste-duplicate', title: { pl: '9.3 Kopiowanie, wklejanie, powielanie', en: '9.3 Copying, Pasting, Duplicating' } },
      { id: 'edit-undo-redo', title: { pl: '9.4 Cofanie i ponawianie - co liczy sie jako jedno dzialanie', en: '9.4 Undo and Redo - What Counts as One Action' } },
      { id: 'edit-pan-zoom', title: { pl: '9.5 Przewijanie i skalowanie plotna', en: '9.5 Panning and Zooming the Canvas' } },
      { id: 'edit-layers', title: { pl: '9.6 Warstwy rysowania i dlaczego symbol nigdy nie wpada pod przewod', en: '9.6 Drawing Layers and Why a Symbol Never Falls Under a Wire' } },
      { id: 'edit-messages-panel', title: { pl: '9.7 Panel Messages', en: '9.7 The Messages Panel' } },
    ],
  },
  {
    id: 'ch10', title: { pl: '10. Format pliku i wymiana z EPW-OS', en: '10. File Format and Exchange With EPW-OS' },
    topics: [
      { id: 'file-contents', title: { pl: '10.1 Co zawiera plik projektu', en: '10.1 What the Project File Contains' } },
      { id: 'file-versioning', title: { pl: '10.2 Wersjonowanie schematu i migracje', en: '10.2 Schema Versioning and Migrations' } },
      { id: 'file-guarantees', title: { pl: '10.3 Co edytor gwarantuje, a czego nie', en: '10.3 What the Editor Guarantees, and What It Does Not' } },
      { id: 'file-epwos-bridge', title: { pl: '10.4 Czy EPW-OS potrafi juz czytac ten format', en: '10.4 Whether EPW-OS Can Already Read This Format' } },
    ],
  },
  {
    id: 'ch11', title: { pl: '11. Rozwiazywanie problemow', en: '11. Troubleshooting' },
    topics: [
      { id: 'ts-meter-wizard-empty', title: { pl: 'Kreator miernika pokazuje pusta liste', en: 'The Meter Wizard Shows an Empty List' } },
      { id: 'ts-cannot-connect-wire-symbol', title: { pl: 'Nie da sie przylaczyc przewodu do symbolu', en: 'A Wire Will Not Connect to a Symbol' } },
      { id: 'ts-wire-not-joining-busbar', title: { pl: 'Przewod nie laczy sie z szyna', en: 'A Wire Does Not Join the Busbar' } },
      { id: 'ts-device-marked-invalid', title: { pl: 'Aparat oznaczony bledem w liscie', en: 'A Device Is Marked With an Error in the List' } },
      { id: 'ts-channel-unavailable', title: { pl: 'Kanal niedostepny przy wyborze', en: 'A Channel Is Unavailable When Choosing One' } },
      { id: 'ts-symbol-red-outline', title: { pl: 'Symbol pokazuje sie z czerwona obwodka', en: 'A Symbol Shows a Red Outline' } },
      { id: 'ts-cannot-delete-location-card', title: { pl: 'Nie da sie usunac lokalizacji albo karty', en: 'A Location or Card Cannot Be Deleted' } },
      { id: 'ts-device-id-locked', title: { pl: 'Id aparatu nie da sie zmienic', en: 'The Device Id Cannot Be Changed' } },
      { id: 'ts-signal-panel-wizard-missing-device', title: { pl: 'Kreator panelu sygnalizacyjnego nie pokazuje oczekiwanego aparatu', en: 'The Signal Panel Wizard Does Not Show an Expected Device' } },
      { id: 'ts-save-disabled', title: { pl: 'Przycisk Zapisz w formularzu aparatu jest nieaktywny', en: 'The Save Button in the Device Form Is Disabled' } },
      { id: 'ts-designation-duplicate', title: { pl: 'Nie da sie zapisac aparatu - duplikat oznaczenia', en: 'A Device Cannot Be Saved - Duplicate Designation' } },
      { id: 'ts-wire-diagonal-rejected', title: { pl: 'Przewod nie chce isc po skosie', en: 'A Wire Will Not Go Diagonally' } },
      { id: 'ts-project-wont-open', title: { pl: 'Plik projektu nie chce sie otworzyc', en: 'A Project File Will Not Open' } },
    ],
  },
  {
    id: 'ch12', title: { pl: '12. Skroty klawiszowe', en: '12. Keyboard Shortcuts' },
    topics: [
      { id: 'shortcuts-all', title: { pl: '12. Skroty klawiszowe', en: '12. Keyboard Shortcuts' } },
    ],
  },
  {
    id: 'ch13', title: { pl: '13. Slownik pojec', en: '13. Glossary' },
    topics: [
      { id: 'glossary-all', title: { pl: '13. Slownik pojec', en: '13. Glossary' } },
    ],
  },
];

export function findTopicMeta(topicId: string): HelpTopicMeta | undefined {
  for (const chapter of HELP_TOC) {
    const topic = chapter.topics.find(t => t.id === topicId);
    if (topic) return topic;
  }
  return undefined;
}

export function findChapterOfTopic(topicId: string): HelpChapterMeta | undefined {
  return HELP_TOC.find(chapter => chapter.topics.some(t => t.id === topicId));
}

export function allTopicIds(): string[] {
  return HELP_TOC.flatMap(chapter => chapter.topics.map(t => t.id));
}
