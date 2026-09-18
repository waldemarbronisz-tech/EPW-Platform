# Integracja MQTT

Połączenie sterownika z brokerem MQTT (Home Assistant): adres, port,
użytkownik, TLS, identyfikator klienta, prefiks tematów, okres
publikacji, strefy nieczułości i mapowania przychodzące (zdalny temat →
lokalny tag `Link.<id>.In<n>`).

**To nastawa projektu, nie ustawienie jednego sterownika.** Broker i
tematy należą do instalacji - po wymianie sterownika nowy dostaje je z
projektem. Panel może je zmienić (Engineer, wpis do dziennika, rewizja
+1 „panel”), a różnica między projektem a sterownikiem jest widoczna w
Sterownik → Nastawy sterownika (na żywo) i można ją przyjąć jednym
przyciskiem, tak jak próg zabezpieczenia.

**Hasła do brokera nie ma w projekcie.** Wpisuje się je raz na panelu
(Ustawienia → MQTT) i zostaje w lokalnym pliku sterownika - ta sama
zasada, co dla PIN-ów i tokenów API.

Ustawienia, które ZOSTAJĄ lokalne (nie wchodzą do projektu, bo opisują
egzemplarz sterownika, nie instalację): język interfejsu, adres i port
REST, retencje historiana, dziennika i historii alarmów, ostrzeżenie o
rozmiarze bazy, sterownik I/O. Widać je w panelu Sterownik → Ustawienia
lokalne sterownika, tylko do odczytu.
