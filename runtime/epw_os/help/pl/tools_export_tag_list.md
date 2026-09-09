# Eksport listy sygnałów (Logic Studio/Synoptic Editor)

**Narzędzia → Eksportuj listę sygnałów...** zapisuje do pliku JSON
każdy tag aktualnie zarejestrowany w tym sterowniku - listę, z której
Logic Studio i Synoptic Editor czytają, co naprawdę istnieje do wyboru
przy budowaniu programu albo ekranu, zamiast zgadywać nazwy. Dostępne
na każdym poziomie dostępu, bez PIN-u - eksport to tylko odczyt, ta
sama zasada "już widoczne na poziomie User", którą dokumentują własne
endpointy `GET` REST API (patrz [REST API](help://api_what)).

Jeśli zamiast pliku dostępne jest żywe połączenie z działającym
sterownikiem, `GET /api/v1/tags/export` zwraca dokładnie tę samą
strukturę przez HTTP, bez uwierzytelniania (ta sama zasada co każdy
inny endpoint REST tylko do odczytu).

## Co jest w pliku

Nagłówek:

- `format_version` - wersja kształtu samego tego pliku. Logic Studio
  powinno odmówić wczytania wersji, której nie rozpoznaje, zamiast
  zgadywać kształt, który mógł się zmienić.
- `exported_at` - kiedy wykonano ten eksport (UTC).
- `project_name` - z jakiego projektu to pochodzi.
- `epw_os_version` - która wersja EPW OS to wygenerowała.
- `tag_count` - ile tagów następuje dalej, do szybkiej kontroli.

Dla każdego tagu:

- `name` - pełna, dokładna nazwa tagu - nigdy się nie zmienia między
  wersjami EPW OS ani eksportami (stała tożsamość, do której Logic
  Studio/Synoptic Editor może zapisać referencję).
- `data_type` - `BOOL` / `INT` / `REAL` / `STRING`.
- `direction` - `READ_ONLY` albo `READ_WRITE`. **Tylko `System.Theme`
  ma dziś `READ_WRITE`** - to jedyny tag, który program logiki ma
  dziś prawo zapisać, żeby przełączyć aktywny motyw wizualny (patrz
  [Motywy wizualne](help://set_theme)). Każdy inny tag - także taki,
  który jakiś moduł odczytuje reaktywnie, jak wejście uzbrojenia/
  rozbrojenia strefy alarmowej - jest w tym eksporcie `READ_ONLY`;
  ogólna rodzina tagów-komend zapisywalnych z logiki jeszcze nie
  istnieje w kodzie (patrz "request_tags" niżej).
- `module` - czytelna etykieta, która część sterownika jest
  właścicielem tego tagu (np. "Intrusion Alarm System", "Digital
  Inputs").
- `group` - własny prefiks nazwy tagu (np. "Security", "DI", "ELA01")
  - użyj tego do zbudowania drzewa, po jednej gałęzi na grupę, dokładnie
    tak, jak już robi to własny, najwyższego poziomu obiekt `groups`
    tej listy (każdy klucz to nazwa grupy, każda wartość to lista nazw
    tagów w niej).
- `description` - jeśli kiedykolwiek ustawiono.
- `is_simulated` - true dla tagu, którego bieżąca wartość pochodzi z
  piaskownicy symulacyjnej, nie z prawdziwego sprzętu ani logiki (np.
  suwaki strony Jakość energii) - przydatne, żeby wyszarzyć je albo
  oznaczyć inaczej w selektorze.
- `unit` - obecne (nie-null) tylko dla skonfigurowanego punktu Wejścia
  Analogowego. Każdy inny tag ma `unit: null`.
- `value` - wartość tagu w chwili eksportu. Wyłącznie informacyjnie -
  do chwili otwarcia pliku może już być nieaktualna; o żywy odczyt
  pytaj `GET /api/v1/tags` (albo `/tags/{name}`).

`request_tags` jest dziś zawsze pustą listą - zarezerwowane dla
przyszłej, osobnej rodziny tagów-komend, które program logiki będzie
mógł zapisywać, żeby o coś poprosić (uzbroić strefę, wymusić wyjście)
przez zadeklarowany, ogólny kontrakt. Ta warstwa jeszcze nie istnieje;
ten klucz istnieje już teraz, żeby Logic Studio miało stałe miejsce, od
którego zacząć czytać, gdy powstanie - bez potrzeby nowej wersji
formatu pliku tylko z tego powodu.

## Czego ten eksport nigdy nie robi

Wykonanie tego eksportu nigdy niczego nie zmienia - tylko czyta
TagManager/plik projektu, nigdy do żadnego z nich nie zapisuje.
Uruchamiaj go tak często, jak potrzebujesz.
