# 7.3 Ramka i budynek

Ramka to czysta grafika ilustrujaca szafe, pomieszczenie albo strefe - bez zaciskow, bez polaczen, bez stanu i bez pola Aparat. Ma dwa warianty: plain (zwykla ramka) i building (budynek), plus opcjonalny tytul umieszczony w lewym gornym rogu albo wysrodkowany u gory.

Rysuje sie ja przeciagnieciem prostokata, tak jak `graphics.rectangle` - z jednym ograniczeniem: minimalny rozmiar to dwa oczka siatki w kazdym wymiarze; przeciagniecie mniejszego prostokata i tak tworzy ramke o rozmiarze minimalnym, nie zerowym.
