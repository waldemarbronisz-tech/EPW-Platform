# Połączenie ze sterownikiem

Adres (np. `http://192.168.1.50:8000`) i token dostępu do REST API
sterownika EPW-OS — zapisywane lokalnie (nie w pliku projektu, bo token
to sekret operatora, nie dane projektu do współdzielenia).

**Testuj połączenie** i **Pobierz podgląd tagów** są prawdziwe — łączą
się z realnymi punktami `/api/v1/health` i `/api/v1/tags` sterownika.

**Wyślij do urządzenia** i **Zgraj z urządzenia** są celowo uczciwie
niepełne: REST API sterownika **nie ma dziś** żadnego punktu do
wysyłania/pobierania konfiguracji projektu ani sprawdzania rewizji —
kliknięcie pokazuje ten fakt wprost, zamiast udawać, że synchronizacja
się powiodła. To wymaga rozszerzenia po stronie runtime, poza zakresem
Studio.
