# Integracja MQTT

**Ustawienia → MQTT...** (poziom Engineer) publikuje stan tego
sterownika do brokera MQTT, żeby Home Assistant albo inny sterownik EPW
mógł z niego skorzystać bez odpytywania REST API. Domyślnie wyłączona —
włączenie jej nigdy nie zmienia działania niczego innego w tym
programie.

## Jedna twarda zasada: wyłącznie publikacja

Ta integracja **nigdy nie może przyjąć rozkazu**. Publikuje wartości
tagów, alarmy i zdarzenia na zewnątrz, i może zostać poproszona o
odczytanie danych jednego innego sterownika do wewnątrz (patrz
"Sygnały przychodzące Link" niżej) — to cała lista tego, co robi. Nie
ma dziś, i nigdy nie będzie, sposobu, żeby przez ten ekran uzbroić
strefę, rozbroić ją, wymusić wyjście albo zmienić nastawę przez MQTT.
Zbudowanie tego wymagałoby własnego projektu uwierzytelniania i
autoryzacji — dokładnie tak, jak schemat tokenów API w REST API powstał
jako osobne zadanie, dopiero po znalezieniu tam realnej luki
omijającej sprawdzanie uprawnień. To nie jest coś, co integracja dokłada
przy okazji.

## Konfiguracja

Adres i port brokera, opcjonalna nazwa użytkownika, TLS włącz/wyłącz,
identyfikator klienta (domyślnie identyfikator projektu), prefiks
tematów (domyślnie `epw/<identyfikator klienta>`) oraz, wyłącznie dla
wartości liczbowych (analogowych), interwał publikacji i strefa
nieczułości (wartość publikuje się ponownie dopiero, gdy minie
zadany czas ORAZ zmiana przekroczy zadany próg — ten sam pomysł, co
własna strefa nieczułości zapisu Historiana, tylko osobny, niezależnie
strojony filtr dla tego jednego odbiorcy).

**Hasło brokera nigdy nie jest zapisywane w pliku projektu ani w
repozytorium.** Mieszka we własnym pliku lokalnym
(`epw_os/config/mqtt.local.json`), zgodnie z tą samą zasadą "nigdy w
project.json", którą kierują się już PIN-y dostępu i tokeny REST API —
choć, inaczej niż one, hasła brokera nie da się zahaszować
jednokierunkowo (ten program musi je wysłać do brokera, jawnie, przy
każdym połączeniu), więc ten jeden plik trzyma prawdziwą wartość, nie
skrót.

## Co jest publikowane

Każdy tag zarejestrowany w TagManagerze, przy każdej zmianie wartości,
jako własny, zatrzymany (retained) temat — klient podłączający się po
starcie od razu widzi bieżący stan, nie tylko przyszłe zmiany. Alarmy
(pojawienie się/ustąpienie/potwierdzenie) i zdarzenia systemu
alarmowego (uzbrojenie, rozbrojenie, alarm, awaria linii) też są
publikowane, jako krótkotrwałe wiadomości zdarzeniowe (niezatrzymane —
zdarzenie to chwila, nie stan). Stan sterownika (online/offline, tryb
pracy, wersja) jest zatrzymany, wsparty testamentem MQTT (**Last Will
and Testament**): jeśli ten program zniknie bez czystego zamknięcia,
sam broker ogłosi go jako offline — odbiorcy nigdy nie zobaczą
zamrożonego, nieaktualnego "wciąż OK".

**Dane symulowane są oznaczone, nie ukryte.** Każdy tag publikuje też
towarzyszący temat "quality" (`GOOD`, `SIMULATED`, `STALE`, ...) — dokładnie
tę samą jakość, którą TagManager już śledzi dla każdego odczytu, więc
wartość bez prawdziwego czujnika za nią (to samo rozróżnienie, co w
[eksporcie listy sygnałów](help://tools_export_tag_list)) nigdy nie
zostanie wzięta przez odbiorcę za pomiar.

Tam, gdzie da się to zrobić automatycznie, wraz z pierwszą wartością
tagu publikowana jest wiadomość wykrywania Home Assistant, więc tag
pojawia się w Home Assistant jako encja bez ręcznej konfiguracji YAML
po tamtej stronie.

## Sygnały przychodzące Link (Link.\*)

**Jedyna** rzecz, jaką ta integracja może przyjąć: ręcznie skonfigurowana
lista mapowań *(zdalny temat MQTT → nazwa lokalnego tagu)*, gdzie
lokalna nazwa ma zawsze postać `Link.<identyfikator>.In<nazwa>`. Każde
z nich staje się zwykłym, tylko-do-odczytu-dla-wszystkich-innych tagiem,
który program logiki może odczytać — dokładnie jak wejście analogowe,
nigdy jako wyzwalacz rozkazu. Mapowanie (i to, jak długo może nie mieć
aktualizacji, zanim uznamy je za nieaktualne) konfiguruje się w tym
samym oknie Ustawienia → MQTT....

**Mapowanie bez aktualizacji dłużej niż jego własny skonfigurowany czas
zostaje oznaczone jako NIEAKTUALNE**, a nie trzyma ostatnią wartość w
nieskończoność — ta sama zasada, którą w tym programie kieruje się już
nadzór łączności z urządzeniami: cicha sieć to nie to samo, co "nic się
nie zmieniło".

## Co robi — i czego nie robi — utrata połączenia

Publikacja nigdy nie blokuje programu. Rozłączony albo nieosiągalny
broker nie może w żaden sposób spowolnić ani wpłynąć na logikę, alarmy
czy sterowanie — najgorszy przypadek to ograniczona, trzymana w pamięci
kolejka jeszcze niewysłanych wiadomości, która przy przepełnieniu
odrzuca NAJSTARSZE wpisy, zamiast rosnąć bez ograniczeń. Ponowne
połączenie jest automatyczne, z rosnącym odstępem między próbami, żeby
broker niedostępny przez dłuższy czas nie został zalany próbami zaraz
po powrocie. Jeśli biblioteki `paho-mqtt` w ogóle nie ma w środowisku,
albo żaden broker nie jest osiągalny, reszta programu i tak startuje i
działa całkowicie normalnie — integracja po prostu pozostaje
nieaktywna, a jej stan połączenia widać od razu w oknie Ustawienia →
MQTT....
