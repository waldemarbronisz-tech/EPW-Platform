# Kopia zapasowa tego sterownika

**Ustawienia → Kopia zapasowa sterownika...**, poziom Engineer, z wpisem
do dziennika.

Projekt jest bezpieczny: leży w EPW Studio, zwykle w repozytorium, i da
się go tu przysłać przez sieć. Cała reszta istnieje **wyłącznie na
karcie tego sterownika**:

- liczniki łączeń — ile razy każdy aparat zadziałał i jak długo
  pracował, od dnia montażu;
- stan uzbrojenia — które strefy były uzbrojone i w jakim trybie;
- pamięć alarmu, wykluczenia, liczniki nadzoru linii;
- bity retencyjne logiki (`MR.` / `MWR.`);
- dziennik audytowy — zapis, kto co zrobił;
- ustawienia lokalne: język, retencje, magistrala.

Padnie karta i nic z tego nie wraca. Kopia zapasowa jest tym, dzięki
czemu wraca.

## Czego kopia nie niesie

**Żadnych sekretów.** Ani PIN-ów dostępu, ani kodu użytkownika
alarmówki, ani tokenu zdalnego, ani tokenów REST API, ani hasła do
brokera MQTT.

Kopia to plik, który opuszcza obiekt: ląduje na laptopie, w mailu, na
pendrivie w samochodzie. PIN ma cztery cyfry, a hasz czterech cyfr jest
o jedną tablicę od bycia tym PIN-em. Więc zostają tutaj.

Kopia niesie zamiast tego **inwentarz** — kto miał kod, kto miał token,
czy tokeny API i hasło brokera były ustawione. Odtworzenie zamienia to
na listę kontrolną z nazwiskami. Nadanie pięciu kodów z listy to
dziesięć minut. Odzyskanie czterech lat liczników łączeń jest
niemożliwe.

**Żadnej historii trendów.** To zarejestrowane pomiary, nie
konfiguracja, i potencjalnie ogromne. Sterownik, który wraca bez
trendów, pracuje; sterownik, który wraca bez stanu uzbrojenia, kłamie
o budynku.

## Kiedy ją robić

Przed zmianą projektu, po uruchomieniu i cyklicznie, jeśli instalacja
jest istotna. Ten sam plik pobiera się też ze Studia (Sterownik → Kopia
zapasowa sterownika) i przez REST
(`GET /api/v1/controller/backup`).
