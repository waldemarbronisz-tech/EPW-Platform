# Tryb prezentacji

Uruchamia przygotowany scenariusz demonstracyjny - zmiany wartości,
komendy i alarmy, według ustalonego harmonogramu - żeby móc pokazać
system w kilka minut bez komentowania i klikania krok po kroku.
Narzędzia > Tryb prezentacji... Poziom Inżyniera.

## Wymaga Trybu ćwiczebnego

Tryb prezentacji **nie może się uruchomić, gdy [Tryb ćwiczebny](help://saf_training_mode)
jest wyłączony** - to twardy wymóg, nie preferencja. Jeśli Tryb
ćwiczebny nie jest jeszcze aktywny w momencie kliknięcia Start, okno
zapyta, czy go włączyć - nigdy nie włączy go samo. To właśnie sprawia,
że scenariusz nigdy nie dotrze do prawdziwego sprzętu - to samo
odcięcie na poziomie warstwy sterowników, które zapewnia już Tryb
ćwiczebny.

## Scenariusze

Scenariusz to plik (`epw_os/presentation_scenarios/*.json`), nie coś
zaszytego w programie - lista kroków z czasami, każdy krok to zmiana
wartości tagu, komenda (przechodząca przez dokładnie tę samą
walidację co prawdziwy przycisk Force - scenariusz nie może pominąć
sprawdzenia uprawnień ani blokady), wywołanie/skasowanie alarmu,
chwilowe "zamilknięcie" urządzenia na magistrali albo tymczasowe
obniżenie progu ostrzegawczego licznika przełączeń na potrzeby
krótkiego pokazu. Wybierz jeden z listy przed kliknięciem Start - jego
opis pokazuje się od razu, więc wiadomo, co się zaraz uruchomi. EPW OS
jest dostarczany z sześcioma:

- **Voltage Sag and Protective Trip** - normalna praca, zapad
  napięcia, alarm niedonapięciowy, zadziałanie zabezpieczenia i
  powrót do normy.
- **Normal Operation and Manual Control** - najprostszy: aparat
  zamyka się i otwiera na rozkaz, z realnym potwierdzeniem sprzężenia
  zwrotnego.
- **Communication Loss and the Fault Latch** - urządzenie przestaje
  odpowiadać; prawdziwe wykrycie po 3 nieudanych cyklach; zatrzask
  zostaje mimo powrotu komunikacji i wymaga ręcznego kwitowania.
- **Overload and Rising Current** - prąd narasta stopniowo (widoczne
  na stronie Trendy), przekracza próg ostrzegawczy, potem zadziałania,
  pojawia się alarm, aparat się otwiera.
- **Command Sent, Never Confirmed** - rozkaz zostaje wysłany, ale
  sprzężenie zwrotne nigdy nie wraca; prawdziwy czas nadzoru komendy
  upływa, a aparat nigdy nie jest pokazany jako zamknięty.
- **Mechanical Wear and Switching Counters** - seria przełączeń
  przekracza (tymczasowo obniżony) próg ostrzegawczy licznika.

Format pliku opisany w `epw_os/presentation_scenarios/README.md`,
jeśli chcesz napisać własny.

## Sterowanie

- **Start** - uruchamia wybrany scenariusz od pierwszego kroku.
- **Pauza / Wznów** - odliczanie do następnego kroku zatrzymuje się i
  później wznawia dokładnie od miejsca, w którym stanęło.
- **Krok dalej** - wykonuje następny krok natychmiast, bez czekania na
  jego zaplanowany czas.
- **Stop** - kończy scenariusz i przywraca każdą wartość, którą
  zmienił (wartości tagów oraz zapisy liczników przełączeń, łącznie z
  tymczasowo obniżonym progiem ostrzegawczym), do stanu sprzed Startu.
  Scenariusz, który dobiegnie końca sam, robi to samo automatycznie -
  nie trzeba klikać Stop tylko po to, żeby posprzątać. Jeden celowy
  wyjątek: prawdziwy zatrzask safety_kernel (patrz
  [Monitorowanie zdrowia systemu](help://saf_kernel)), do którego
  doprowadzi scenariusz, nigdy nie jest kasowany przez Stop ani nic
  innego poza rzeczywistym, ręcznym potwierdzeniem na stronie Alarmy -
  patrz "Communication Loss and the Fault Latch" wyżej.

## Wskaźnik

Osobny znaczek na pasku statusu, niezależny od wskaźnika Trybu
ćwiczebnego, pokazuje się, gdy trwa prezentacja - to dwa niezależne
sygnały (zwykle zobaczysz oba naraz, bo Tryb prezentacji wymaga Trybu
ćwiczebnego), nie jeden zastępujący drugi.

## Dziennik audytowy

Uruchomienie i zatrzymanie prezentacji są zapisywane do
[Dziennika audytowego](help://ea_audit_log), tak jak każda inna
czynność istotna dla bezpieczeństwa.
