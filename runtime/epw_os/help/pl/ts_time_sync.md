# Wskaźnik synchronizacji czasu na czerwono

Wskaźnik "Time Sync" na dolnym pasku statusu pokazuje, czy zegar
systemowy komputera, na którym działa EPW OS, jest zsynchronizowany z
usługą czasu systemu operacyjnego (Windows Time / timedatectl / chrony
— zależnie od systemu). **Na czerwono** oznacza NOT SYNCED — czas
komputera nie jest potwierdzony jako prawidłowy.

Najedź kursorem na wskaźnik, żeby zobaczyć szczegóły (nazwę źródła
czasu, czy usługa NTP jest w ogóle skonfigurowana).

## Co sprawdzić

1. Czy komputer ma dostęp do sieci ze źródłem czasu (serwer NTP w
   sieci zakładowej albo internet).
2. Czy usługa synchronizacji czasu w systemie operacyjnym jest
   uruchomiona.
3. Czy data/godzina w systemie operacyjnym są w ogóle sensowne.

## Dlaczego to ważne

Nieprawidłowy czas systemowy oznacza nieprawidłowe znaczniki czasu w
rejestrze zdarzeń, dzienniku audytowym i eksportowanych danych
historycznych — utrudnia to później odtworzenie przebiegu zdarzeń.
Wskaźnik jest wyłącznie informacyjny — nie blokuje żadnej funkcji
programu.
