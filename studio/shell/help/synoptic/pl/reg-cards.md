# 3.2 Karty wejsc i wyjsc

Karta reprezentuje fizyczna karte wejsc/wyjsc sterownika: identyfikator (np. `ELA1`), model (etykieta opisowa, dowolny tekst), rodzaj kanalow (DI, DO, AI albo AO - jedna karta ma jeden rodzaj) i liczbe kanalow. Kanaly numerowane sa od 1.

Rejestr kart daje dwie rzeczy: (1) walidacje kazdego adresu kanalu w formularzu aparatu - czy karta istnieje, czy jej rodzaj zgadza sie z rodzajem uzytym w adresie, czy numer kanalu miesci sie w zakresie 1..liczba_kanalow (`validateChannelAddress`); (2) wykrywanie podwojnego przypisania tego samego kanalu do dwoch roznych aparatow (`CHANNEL_ADDRESS_COLLISION`) - pikcer kanalu w formularzu aparatu od razu wyszarza kazdy kanal juz zajety, pokazujac przez kogo.

Bez zadnej karty w rejestrze nie da sie wpisac zadnego poprawnego adresu kanalu - kazdy picker kanalu w formularzu aparatu filtruje karty po rodzaju wymaganym dla danego pola (np. picker `input` aparatu MEASURED pokazuje tylko karty AI).
