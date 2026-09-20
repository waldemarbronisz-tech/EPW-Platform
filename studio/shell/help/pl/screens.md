# Schemat synoptyczny

Edytor ekranów (Synoptic Editor) jako dział Studia. Rysujesz to, co
operator zobaczy na sterowniku — i wiążesz rysunek z prawdziwymi
punktami i aparatami.

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
