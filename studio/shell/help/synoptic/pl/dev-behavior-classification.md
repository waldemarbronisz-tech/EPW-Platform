# 4.3 Klasyfikacja po zachowaniu, nie po rodzaju urzadzenia

Aparat jest klasyfikowany po ZACHOWANIU, a nie po rodzaju urzadzenia. Pole `kind` (np. "contactor", "valve", "sensor") to WYLACZNIE etykieta opisowa bez znaczenia funkcjonalnego - nie wplywa na zadna regule walidacji ani na to, jakie pola aparat ma. O tym, jakie pola, sygnaly i komendy ma aparat, decyduje wylacznie pole `behavior`.

Sa dokladnie cztery zachowania, i nic wiecej nie moze byc po cichu dodane: SWITCHED ([4.4](help://synoptic/dev-switched)), SIGNAL ([4.5](help://synoptic/dev-signal)), MEASURED ([4.6](help://synoptic/dev-measured)), MODULATED ([4.7](help://synoptic/dev-modulated)). Wybor zachowania w formularzu zmienia caly dolny formularz - a jesli aparat mial juz wypelnione pola szczegolowe innego zachowania, zmiana pyta o potwierdzenie, bo je wyczysci.
