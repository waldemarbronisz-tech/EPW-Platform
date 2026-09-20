# Odtworzenie z kopii zapasowej

**Ustawienia → Odtwórz z kopii zapasowej...**, poziom Engineer, z wpisem
do dziennika.

## Co się dzieje

1. Plik jest czytany i sprawdzany: format, wersja schematu i suma
   kontrolna całej kopii. Plik zmieniony albo ucięty po zapisaniu jest
   **odrzucany, zanim cokolwiek zostanie ruszone** — odtworzenie nigdy
   nie jest wykonane do połowy.
2. Dostajesz do obejrzenia, co w nim jest — jaki projekt, jaka rewizja,
   ile liczników, które strefy były wtedy uzbrojone — **zanim**
   cokolwiek zostanie nadpisane.
3. Na „tak": projekt, plik stanu i ustawienia lokalne są zapisywane,
   a sterownik **przebudowuje się według nich bez restartu** (ta sama
   przebudowa, przez którą przechodzi
   [wgranie projektu](help://proj_install)).
4. Dostajesz listę tego, czego nikt nie mógł odtworzyć za Ciebie.

## Czego nie nadpisuje

Ustawień, które opisują **ten** sterownik, a nie instalację: jego adresu
REST, sterownika wejść/wyjść i ścieżek plików. Zamiennik stoi w innej
sieci i może mieć inną magistralę, a kopia pochodzi ze sprzętu, który
padł.

## Stan uzbrojenia wraca taki, jaki był

Strefa, która była uzbrojona, wraca uzbrojona, w tym samym trybie. To ta
sama zasada, którą sterownik stosuje przy własnym restarcie —
odtworzenie jest restartem z dodatkowymi krokami — i trafia do dziennika.
Sterownik, który wróciłby rozbrojony, kłamałby o budynku.

## Lista kontrolna

Kończy każde odtworzenie, bo kopia celowo nie niesie sekretów (patrz
[Kopia zapasowa tego sterownika](help://backup_what)):

- PIN-y dostępu — [Zmiana PIN-u](help://al_change_pin);
- kod na klawiaturę i token zdalny każdego użytkownika, po nazwisku —
  [Użytkownicy alarmówki](help://intr_users);
- tokeny REST API;
- hasło do brokera MQTT — [MQTT](help://mqtt_what).

Dopóki nie zostaną nadane, sterownik pracuje na właściwej instalacji, ze
świeżo wygenerowanymi PIN-ami, których nikt nie zna.
