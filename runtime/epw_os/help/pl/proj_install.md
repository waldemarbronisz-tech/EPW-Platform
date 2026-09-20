# Wgranie projektu

**Plik → Otwórz**, poziom Engineer, z wpisem do dziennika. Tak projekt
zaprojektowany w EPW Studio wchodzi do pracy na tym sterowniku.

## Co się dzieje, po kolei

1. Plik czyta **ten sam czytnik, którym pisze Studio**. Plik przez niego
   odrzucony niczego nie zastępuje — dostajesz powód.
2. Poprzedni projekt zostaje jako `projekt.epw.bak`.
3. Panel pyta, czy **przebudować sterownik teraz, bez restartu**.
4. Na „tak": karty, tagi kanałów, sterownik magistrali, rejestr
   urządzeń, aparaty, komendy, użytkownicy alarmówki, moduły ze składu,
   opisy punktów, definicje komend i program logiki są przebudowywane
   z nowego pliku, a razem z nimi to okno.

Odmowa nie jest porażką — plik jest wgrany i zadziała przy następnym
starcie sterownika, tak jak działo się to zawsze.

## Co przebudowa na chwilę zatrzymuje

Skan logiki i alarmówkę, na tyle, ile przebudowa trwa.
[Wymuszenia](help://dio_force) są zdejmowane na początku, celowo:
wymuszenie przypina tag, którego nowy projekt może w ogóle nie mieć.

Wszystko, co przeżywa projekty, pracuje dalej — baza, rejestracja
historyczna, safety kernel, MQTT, REST, dziennik audytowy i poziom
dostępu, na którym jesteś zalogowany.

## Co znika i dlaczego tak jest dobrze

Karta skasowana w Studiu **zabiera swoje tagi kanałów**. Aparat
skasowany w Studiu przestaje dawać się sterować. Kanał, którego nie ma
nigdzie w urządzeniu, nie powinien zostawać na panelu do odczytu na
zawsze.

## Gdy nowego pliku nie da się wczytać przy późniejszym starcie

Poprzedni projekt wraca sam z `.bak`, a odrzucony zostaje do obejrzenia.
Sterownik zgłasza to jako problem startowy, zamiast startować na niczym.

## Wysyłka ze Studia zamiast tego

To samo dzieje się, gdy Studio wyśle projekt przez REST — patrz [REST
API](help://api_what). Studio najpierw porównuje rewizje i zatrzymuje
się, jeśli ten sterownik w międzyczasie poszedł dalej.
