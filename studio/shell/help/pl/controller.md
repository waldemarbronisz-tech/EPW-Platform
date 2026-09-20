# Połączenie ze sterownikiem

Stąd projekt trafia na sterownik i stąd widać, co on naprawdę robi.

## Połączenie

**Adres (URL)** i **token dostępu** (Engineer — wydany na panelu
sterownika), potem **Testuj połączenie**. Stan pokazuje się obok:
nieznany / sprawdzanie / połączenie OK / błąd z powodem.

## Synchronizacja projektu

### Wyślij na urządzenie

1. **Projekt musi być zapisany** — sterownik dostaje plik z dysku, nie
   zawartość okna. Studio zaproponuje zapis.
2. Studio pobiera nagłówek sterownika i porównuje **rewizję**
   i **odcisk nastaw**.
3. Jeśli nastawy się rozjechały — tabela różnic: nastawa, wartość
   w Studiu, wartość na sterowniku. Możesz wysłać i nadpisać albo
   anulować.
4. Jeśli sterownik zmienił rewizję w międzyczasie, **nic nie jest
   wysyłane** i dostajesz o tym komunikat. Rozjazd = zatrzymać się.
5. Sterownik **przebudowuje się według nowego projektu bez restartu**:
   karty, punkty, aparaty, komendy, alarmówka, zabezpieczenia, logika
   i panel. Komunikat mówi wprost, czy tak się stało.

### Odbierz z urządzenia

Ściąga `projekt.epw` dokładnie w postaci, w jakiej sterownik z nim
pracuje — z nastawami zmienionymi na panelu i z notatkami serwisowymi,
które tam powstały.

## Podgląd na żywo

**Pobierz podgląd tagów** — tabela tag / wartość / jakość. Ten sam
kanał zasila tryb „Na żywo" w [rejestrze punktów](help://points),
w [kartach](help://io_cards) i w [edytorze ekranów](help://screens).

## Nastawy sterownika (na żywo)

**Pobierz nastawy**, opcjonalnie **odświeżaj co 5 s** i **tylko
różnice**. Tabela: nastawa / Studio / sterownik, z podświetleniem
rozbieżności.

**Przyjmij nastawy sterownika do projektu** przepisuje wartości ze
sterownika do projektu — to jest droga powrotna dla nastaw, które ktoś
poprawił przy szafie. Trzeba potem zapisać projekt.

## Ustawienia lokalne sterownika

**Pobierz ustawienia lokalne** — tylko do odczytu: język interfejsu,
REST, retencje historiana i dziennika, sterownik I/O, ścieżki plików.
To są ustawienia **egzemplarza**, nie instalacji, więc nie ma ich
w projekcie — ale nic na sterowniku nie jest niewidoczne ze Studia.

## Kopia zapasowa sterownika

**Pobierz kopię zapasową...** ściąga wszystko, co istnieje tylko na tym
sterowniku: liczniki łączeń, stan uzbrojenia, pamięć alarmu, bity
retencyjne logiki, dziennik audytowy, ustawienia lokalne i sam projekt.

Nie niesie **żadnych sekretów** — ani PIN-ów, ani kodów użytkowników
alarmówki, ani tokenów, ani hasła do brokera. Kopia to plik, który
opuszcza obiekt, a hasz czterocyfrowego PIN-u nie jest sekretem. Niesie
zamiast tego inwentarz: kto co MIAŁ, dzięki czemu odtworzenie kończy się
listą kontrolną z nazwiskami.

**Odtwórz z kopii zapasowej...** najpierw prosi sterownik o opisanie
kopii, pokazuje, co zostanie nadpisane, i dopiero wtedy ją wysyła.
Sterownik przebudowuje się według niej bez restartu. Własny adres REST
i sterownik wejść/wyjść zamiennika zostają nietknięte — opisują sprzęt,
na którym on pracuje, a nie ten, który padł.

Całą procedurę wymiany opisuje pomoc samego sterownika, rozdział „Kopia
zapasowa i wymiana".

## Liczniki łączeń

**Pobierz liczniki** — punkt, liczba załączeń, wyłączeń, czas w stanie
zamkniętym, próg ostrzegawczy (z [rejestru punktów](help://points)).

**Zeruj wybrany** / **Zeruj wszystkie** — nieodwracalne, wymagają tokenu
Engineer, trafiają do dziennika. Próg ostrzegawczy zostaje.

Sterownik bez modułu Liczników łączeń mówi to wprost, zamiast pokazywać
pustą tabelę.

## Stan logiki

Jedna linia, odświeżana razem z resztą:

- **RUNNING** — ile bloków, czas cyklu, liczba skanów, najdłuższy skan,
  ile wyjść prowadzi logika;
- **STOPPED** — program jest wczytany, ale skan nie chodzi: **blokady
  z tego programu nie są liczone**;
- **brak** — sterownik pracuje bez logiki użytkownika;
- **NOT running** — program został odrzucony, z powodem.
