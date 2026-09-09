# Diagnostyka magistrali

Statystyki komunikacji per urządzenie na magistrali - zbudowana już
teraz, na symulatorze, żeby była gotowa w dniu, w którym powstanie
prawdziwy sterownik szeregowy (Modbus RTU/TCP). Poziom Inżyniera.

## Co znaczy każda kolumna

- **Wysłane / Odebrane** — ramki wysłane do tego urządzenia i ramki
  faktycznie odebrane z powrotem, od ostatniego zerowania.
- **Timeout / CRC / Niepoprawna** — trzy osobne liczniki błędów: brak
  jakiejkolwiek odpowiedzi, niezgodność sumy kontrolnej i odpowiedź,
  która dotarła, ale była nieprawidłowa (zła długość, nieoczekiwana
  treść).
- **Ostatni / Średni / Najgorszy (ms)** — czas odpowiedzi ostatniej
  udanej wymiany, średnia ze wszystkich oraz najwolniejszy
  zarejestrowany, od ostatniego zerowania.
- **Od sukcesu** — ile czasu upłynęło, odkąd to urządzenie ostatnio
  odpowiedziało poprawnie.
- **Sukces %** — procent wysłanych ramek, które doczekały się
  poprawnej odpowiedzi.

## Dziś, na symulatorze

Nie ma jeszcze prawdziwej magistrali - każde urządzenie jest obsługiwane
przez symulator, więc liczniki błędów zostają na zerze (nie ma czego
nie udać) a pokazane czasy odpowiedzi to rzeczywisty, zmierzony koszt
samej symulowanej wymiany, nie zmyślona liczba. Będą bardzo małe - to
uczciwe, nie placeholder.

## Ostatnie błędy

Pod tabelą, najnowsze błędy ze wszystkich urządzeń, od najnowszego, ze
znacznikiem czasu i krótkim opisem tego, co poszło nie tak.

## Zeruj wszystkie liczniki

Zeruje liczniki każdego urządzenia (ramki, błędy, czasy odpowiedzi) i
czyści listę ostatnich błędów. Nie ma możliwości zresetowania liczników
tylko jednego urządzenia z tej strony - to reset całej tablicy,
zgodnie z praktyką rozruchową ("wyczyść wszystko, zacznij czysty
przebieg").
