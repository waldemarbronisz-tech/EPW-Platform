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
