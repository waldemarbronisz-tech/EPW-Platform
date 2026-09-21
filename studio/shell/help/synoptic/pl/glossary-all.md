# 13. Slownik pojec

**Adres kanalu** — Tekstowy adres w formacie KARTA.RODZAJ.KANAL wskazujacy fizyczny kanal wejscia/wyjscia, np. ELA1.DI.12. [→](help://synoptic/reg-addressing)

**Aparat** — Jednostka konfiguracji zdefiniowana raz w Liscie aparatow; symbol na ekranie tylko wskazuje na nia po identyfikatorze. [→](help://synoptic/dev-why-not-in-screen)

**Dioda sygnalizacyjna** — Symbol z trzema dopuszczalnymi stanami: ON, OFF i QUALITY. [→](help://synoptic/elem-indicator-diode)

**EPW-Logic-Studio** — Aplikacja platformy EPW budujaca automatyke: regoly sterowania, blokady i sekwencje. [→](help://synoptic/intro-platform)

**EPW-OS** — Aplikacja uruchomieniowa platformy EPW - wyswietla ekrany i pracuje na prawdziwym sprzecie. [→](help://synoptic/intro-platform)

**Historia cofniec** — Ciag migawek stanu rysunku, po jednej na kazde zapisane dzialanie, z limitem 100 wpisow. [→](help://synoptic/edit-undo-redo)

**Home Assistant** — Warstwa dodatkowa (podglad/powiadomienia przez pole publishToHa), nigdy tor sterowania. [→](help://synoptic/intro-platform)

**Identyfikator (id)** — Niezmienny klucz maszynowy aparatu, np. KOT_KMG1 - lokalizacja jest z niego wyliczana. [→](help://synoptic/dev-naming)

**Kanal** — Pojedyncze wejscie albo wyjscie na karcie, numerowane od 1. [→](help://synoptic/reg-cards)

**Karta** — Rejestrowa reprezentacja fizycznej karty I/O sterownika: identyfikator, rodzaj kanalow, ich liczba. [→](help://synoptic/reg-cards)

**Kolizja kanalow** — Sytuacja, gdy dwa aparaty wskazuja na ten sam fizyczny kanal - wykrywana i sygnalizowana przy zapisie. [→](help://synoptic/dev-form-validation)

**Kropka wezlowa** — Znacznik w punkcie siatki, gdzie spotykaja sie trzy lub wiecej galezi przewodow/zaciskow. [→](help://synoptic/sch-junction-dot)

**Licznik przelaczen** — Opcjonalne zliczanie przelaczen aparatu SWITCHED (sygnal .COUNTER) - bez wbudowanego progu ostrzegawczego. [→](help://synoptic/dev-switched)

**Lokalizacja** — Krotki, wielkoliterowy przedrostek identyfikatora aparatu, np. KOT. [→](help://synoptic/reg-locations)

**Miernik** — Dynamiczny element ekranu zlozony z wierszy pomiarowych, o wysokosci wyliczanej automatycznie. [→](help://synoptic/elem-meter)

**Migracja** — Automatyczne przeksztalcenie starszego pliku projektu do biezacego ksztaltu przy wczytaniu. [→](help://synoptic/file-versioning)

**Osrodek** — Jeden z trzech rodzajow instalacji, do ktorego nalezy przewod: prad, woda albo wentylacja. [→](help://synoptic/sch-media)

**Oznaczenie** — To, co widac na schemacie przy symbolu, np. -K1 - odrebne od identyfikatora aparatu. [→](help://synoptic/dev-naming)

**Panel sygnalizacyjny** — Dynamiczny element ekranu jak miernik, ale kazdy wiersz konczy sie dioda dwustanowa. [→](help://synoptic/elem-signal-panel)

**Plik projektu** — Plik .epwsyn (JSON, format EPW_SYNOPTIC) zawierajacy caly stan projektu. [→](help://synoptic/file-contents)

**Podglad edytora** — Recznie ustawiony stan pokazywany na symbolu podczas projektowania - nigdy odczyt z prawdziwego sprzetu. [→](help://synoptic/sym-states-preview)

**Punkt graniczny** — Symbol reprezentujacy miejsce, w ktorym instalacja laczy sie ze swiatem zewnetrznym - zrodlo albo odplyw. [→](help://synoptic/sch-boundary-point)

**Ramka** — Czysta grafika ilustrujaca szafe, pomieszczenie albo strefe - bez zaciskow i bez pola Aparat. [→](help://synoptic/elem-frame-building)

**Rejestr** — Wspolna lista projektu (lokalizacje, karty albo aparaty), z ktorej ekran tylko czerpie przez odwolania. [→](help://synoptic/reg-locations)

**Rozbieznosc** — Sytuacja, gdy polecenie wyslane do aparatu SWITCHED nie zostalo potwierdzone przez wejscie zwrotne w ustalonym czasie. [→](help://synoptic/dev-switched)

**Sprzezenie zwrotne** — Wejscie (albo dwa) potwierdzajace rzeczywisty stan aparatu SWITCHED - tryb DUAL, SINGLE albo NONE. [→](help://synoptic/dev-switched)

**Stan bezpieczny** — Zachowanie aparatu zdefiniowane na wypadek startu albo utraty lacznosci - nalezy do sprzetu, nie do ekranu. [→](help://synoptic/dev-switched)

**Sygnal zakazu** — Sygnal pozwalajacy logice ZABRONIC wykonania polecenia, nie tylko je wyslac. [→](help://synoptic/dev-signals-commands)

**Szyna zbiorcza** — Przewod w stylu BUS, wizualnie grubszy, przeznaczony do podlaczania wielu odbiorow na calej dlugosci. [→](help://synoptic/sch-wire-style)

**Walidacja na zywo** — Sprawdzanie formularza aparatu przy kazdej zmianie pola, blokujace Zapisz dopoki istnieje blad. [→](help://synoptic/dev-form-validation)

**Wersja schematu** — Numer w pliku projektu rosnacy wylacznie przy zmianie niezgodnej wstecz. [→](help://synoptic/file-versioning)

**Wezel** — Punkt siatki, w ktorym przewody i zaciski moga sie geometrycznie stykac, tworzac jedna siec. [→](help://synoptic/sch-node-model)

**Zachowanie** — To, co klasyfikuje aparat: SWITCHED, SIGNAL, MEASURED albo MODULATED - nie jego rodzaj opisowy. [→](help://synoptic/dev-behavior-classification)

**Zacisk** — Punkt symbolu, w ktorym moze sie z nim stykac przewod - zawsze na srodku jednej z czterech krawedzi. [→](help://synoptic/sym-terminals)
