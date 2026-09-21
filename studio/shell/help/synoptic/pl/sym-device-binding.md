# 6.4 Powiazanie symbolu z aparatem

Kazdy symbol (poza czysta grafika i liniami) ma we Properties pole Aparat - rozwijana liste wszystkich aparatow projektu. Symbol BEZ przypisanego aparatu jest w pelni poprawnym stanem - to czysta grafika bez zadnego zwiazku z lista aparatow.

Wybranie aparatu, gdy pole Oznaczenie symbolu jest puste, automatycznie wypelnia je oznaczeniem tego aparatu - ale TYLKO jednorazowo, w momencie wyboru, i TYLKO gdy bylo puste. Zmiana oznaczenia aparatu pozniej nie zmienia juz wpisanego oznaczenia symbolu (a wpisanie czegos innego recznie do Oznaczenia nigdy nie jest nadpisywane przez ponowny wybor aparatu).

Ten sam aparat przypisany do wielu roznych symboli jest poprawny i nie zglasza zadnego bledu - patrz [4.1](help://synoptic/dev-why-not-in-screen). Symbol wskazujacy na identyfikator aparatu, ktory nie istnieje juz w rejestrze (np. zostal usuniety), nadal renderuje sie normalnie, ale dostaje przerywana czerwona obwodke i trafia do panelu Messages jako ostrzezenie - patrz [9.7](help://synoptic/edit-messages-panel) i [rozdzial 11](help://synoptic/ts-symbol-red-outline).
