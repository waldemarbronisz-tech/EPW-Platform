# 7.2 Panel sygnalizacyjny

Panel sygnalizacyjny to ten sam mechanizm co miernik ([7.1](help://synoptic/elem-meter)), ale kazdy wiersz konczy sie DIODA dwustanowa zamiast pola wartosci. Wiersz albo wskazuje na aparat, albo jest wierszem recznym z wlasnym stanem diody ustawionym wprost (ON/OFF/QUALITY).

Kreator panelu (przycisk Kreator...) pokazuje aparaty SIGNAL i SWITCHED, pogrupowane po LOKALIZACJI (nie po jednostce, jak kreator miernika) - MEASURED nigdy sie tu nie pojawia, bo nie ma pojecia "zamkniety/otwarty" do zasygnalizowania diodą.

Wiersz wskazujacy na prawidlowy aparat SIGNAL/SWITCHED zawsze pokazuje diode w stanie ON w podgladzie - to reczny podglad projektowy (edytor nie ma zywych danych), nie odczyt rzeczywistego stanu stykow. Wiersz wskazujacy na aparat, ktory nie istnieje albo ma inne zachowanie (np. MEASURED), pokazuje diode QUALITY zamiast rzucac wyjatek.
