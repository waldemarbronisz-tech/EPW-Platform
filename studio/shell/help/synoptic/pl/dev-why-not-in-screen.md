# 4.1 Dlaczego konfiguracja aparatu nie siedzi w ekranie

W tym edytorze aparat jest zdefiniowany RAZ, we wspolnej liscie projektu (Aparaty > Lista aparatow...). Element ekranu (symbol na schemacie, wiersz miernika, wiersz panelu sygnalizacyjnego) nigdy nie przechowuje konfiguracji aparatu - mowi tylko "w tym miejscu, tym symbolem, pokaz aparat KOT_KMG1", przez pole przechowujace jego identyfikator.

Ten sam aparat pokazany na wielu symbolach albo nawet na wielu ekranach jest CELEM tej architektury, a nie bledem do wykrycia. Zaznaczenie dwoch roznych symboli wskazujacych na ten sam identyfikator aparatu nie zglasza zadnego bledu ([6.4](help://synoptic/sym-device-binding)) - to normalny, poprawny stan.

Wewnetrznie: `SynopticObject.deviceId` (symbol), `MeterElementRow.device` (wiersz miernika) i odpowiadajace pole wiersza panelu sygnalizacyjnego to zawsze BAJTY IDENTYFIKATORA, nigdy kopia pol aparatu. Jednostka i format miernika ([7.1](help://synoptic/elem-meter)) sa zawsze czytane z aparatu w momencie wyswietlania, nigdy nie kopiowane na wiersz - zmiana jednostki na aparacie natychmiast zmienia to, co pokazuje kazdy wiersz, ktory na niego wskazuje.
