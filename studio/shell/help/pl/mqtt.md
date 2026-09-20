# Integracja MQTT

Połączenie sterownika z brokerem MQTT (zwykle Home Assistant). To jest
**nastawa projektu**: jedzie z projektem na sterownik, panel może ją
zmienić (Engineer, z wpisem do dziennika), a różnice widać w
[Nastawach sterownika na żywo](help://controller).

## Broker

| Pole | Znaczenie |
|---|---|
| **Integracja MQTT włączona** | główny włącznik |
| **Adres brokera / Port** | gdzie się łączyć |
| **Użytkownik** | konto na brokerze |
| **TLS** | połączenie szyfrowane |
| **Client id** | identyfikator klienta na brokerze |
| **Prefiks tematów** | początek wszystkich tematów, domyślnie `epw/<id sterownika>` |
| **Interwał publikacji** | jak często wystawiać stan |
| **Domyślna strefa nieczułości** | o ile wartość musi się zmienić, żeby warto było ją publikować |
| **Limit kolejki** | ile wiadomości trzymać, gdy brokera nie ma |

**Hasła tu nie ma.** Wpisuje się je raz, na panelu sterownika
(Ustawienia → MQTT) i tam zostaje.

## Mapowania przychodzące (temat → tag `Link.*`)

Zdalny temat zasila lokalny tag `Link.<id>.In<n>` podanego typu.
Wartość starsza niż **„nieaktualna po"** jest oznaczana jako
nieaktualna, zamiast udawać świeżą.

Wiersze pochodzące z [Powiązań obiektu](help://object_links) są
oznaczone i **usuwa się je tam**, nie tutaj — Studio nigdy nie rusza
mapowań wpisanych ręcznie.

## Strefy nieczułości per tag

Osobna tabela dla punktów, które mają mieć inną czułość niż domyślna —
np. temperatura co 0,1°C, a ciśnienie co 0,01 bara.

## Sterowanie z Home Assistanta

Łącze nie jest już tylko podglądem: HAOS może uzbrajać i rozbrajać
alarmówkę, kasować alarm, wyciszać sygnalizator, zmieniać nastawy
zabezpieczeń i wydawać komendy aparatom. **Wymuszenia celowo zostają
poza tym kanałem** — to narzędzie kogoś stojącego przy szafie.

Tożsamość jedzie w wiadomości (token per osoba, wydawany na panelu —
patrz [Użytkownicy alarmówki](help://intrusion_users)), bo Home
Assistant ma jedno konto MQTT i broker nie odróżniłby dwóch osób.
Odrzucona komenda wygląda jak włam i podnosi **cichy alarm**.
