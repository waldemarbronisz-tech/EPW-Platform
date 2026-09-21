# 10.4 Czy EPW-OS potrafi juz czytac ten format

NIE, nie w pelni - sprawdzone bezposrednio w kodzie EPW-OS. Istnieje tam `SynopticRuntimeAdapter` (`epw_os/gui/widgets/synoptic_runtime.py`), ktory sprawdza pole `format === "EPW_SYNOPTIC"` i wczytuje tablice `objects` - ale to jawnie oznaczony w kodzie "uproszczony, mockowy" szkielet.

Ten szkielet NIE czyta w ogole `connections` (czyli calego modelu wezlowego, [5.1](help://synoptic/sch-node-model)), NIE czyta `devices`/`locations`/`cards` (calego rejestru aparatow, rozdzial 4), a jego wlasna obsluga kliknieca zaklada, ze `bindings.command` to zwykly tekst w postaci "cel.akcja" - podczas gdy w tym edytorze `bindings.command` to obiekt `{tag, data_type, access}`, nie tekst. Wywolanie tej sciezki dzisiaj skonczyloby sie bledem, nie dzialaniem.

Komentarz we wlasnym kodzie EPW-OS (`epw_os/gui/main_window.py`) mowi to wprost: strona glowna "bedzie hostowac przelaczalne ekrany synoptyki, gdy integracja z Synoptic Editor wyladuje" - czyli jeszcze nie wyladowala. Most miedzy plikiem tego edytora a dzialajacym ekranem w EPW-OS jeszcze nie istnieje.
