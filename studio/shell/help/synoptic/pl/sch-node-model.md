# 5.1 Model wezlowy polaczen

Przewod na schemacie to swobodnie rysowana lamana ortogonalna (tylko odcinki poziome i pionowe) - NIE para portow. Dwa przewody, albo przewod i zacisk symbolu, naleza do TEJ SAMEJ sieci elektrycznej/wodnej/wentylacyjnej wylacznie dlatego, ze dotykaja sie GEOMETRYCZNIE - w tym samym punkcie siatki.

Dotkniecie moze byc na SRODKU odcinka innego przewodu, nie tylko na jego koncu - to wlasnie umozliwia szyne zbiorcza ([5.4](help://synoptic/sch-wire-style)): kazdy przewod stykajacy sie z dowolnym punktem jej dlugosci nalezy do tej samej sieci.

Brak portow upraszcza edycje: mozna przesunac zacisk symbolu (zmieniajac jego rozmiar - [6.2](help://synoptic/sym-terminals)) albo przeciagnac wezel przewodu, a polaczenie ISTNIEJE dopoki punkty faktycznie sie stykaja, bez zadnego osobnego "polaczenia" do naprawienia albo utracenia. Siec jest przeliczana na nowo z samej geometrii (`resolveNets` w `NetResolver.ts`), nigdy nie jest zapisana wprost w pliku projektu.
