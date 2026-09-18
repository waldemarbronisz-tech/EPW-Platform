# Rejestr punktów

**Na żywo i wymuszanie.** Przycisk „Na żywo ze sterownika" na pasku
głównym dopisuje kolumnę z wartością każdego punktu odczytaną ze
sterownika (jakość inna niż GOOD w nawiasie, tło pomarańczowe). Tryb
wymuszania (ikona kłódki w pasku rejestru, po dialogu z zasadami, token
Engineer) pozwala z menu wiersza wymusić wartość albo zdjąć wymuszenie;
wymuszony punkt jest czerwony z „F →". „Zdejmij wszystkie wymuszenia"
albo wyłączenie trybu zdejmuje wszystko; sterownik zdejmuje sam po
utracie łączności ze Studio i po restarcie. Tor zabezpieczeniowy nie
podlega wymuszaniu.

Każdy kanał każdej karty ma tu swój wiersz — pusty, dopóki go nie
nazwiesz. Kolumny:

- **Adres** — kartowy, tylko do odczytu (`ELA1.DI.1`).
- **Opis** — nazwa punktu, np. "Wyłącznik główny — załączony".
- **Lokalizacja** — z listy Lokalizacji.
- **Notatka techniczna** — wolny tekst dla serwisanta (zacisk, przewód).
- **Typ sygnału / Raw min/max / Eng min/max / Jednostka / Miejsca
  dziesiętne** — skalowanie, tylko dla punktów analogowych (AI/AO);
  wyszarzone i chowane dla DI/DO przefiltrowanych do jednej karty.
- **Aparat** — tylko do odczytu: który aparat (z Rejestru aparatów)
  już zajął ten punkt, jeśli którykolwiek.

Filtr **Karta** u góry ogranicza widok do jednej karty naraz.
