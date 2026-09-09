# REST API: endpointy, uwierzytelnianie, wystawienie do sieci

EPW OS uruchamia niewielkie REST API na własnym wątku w tle przy
każdym starcie programu - to nie jest coś, co włącza się osobno.
Domyślnie nasłuchuje wyłącznie na tym komputerze (`127.0.0.1:8000`),
z myślą o integracjach działających na tej samej maszynie (skrypt,
panel, inny program).

## Endpointy

- `GET /api/v1/health` - stany zdrowia podsystemów.
- `GET /api/v1/tags` - aktualna wartość/jakość każdego tagu (opcjonalnie
  `?prefix=DI`, żeby zawęzić do jednej rodziny tagów).
- `GET /api/v1/tags/export` - pełna lista sygnałów, dla Logic Studio/
  Synoptic Editora - patrz
  [Eksport listy sygnałów](help://tools_export_tag_list).
- `GET /api/v1/tags/{name}` - jeden konkretny tag.
- `GET /api/v1/alarms` - aktualnie aktywne alarmy.
- `POST /api/v1/commands` - wydanie komendy (otwarcie/zamknięcie
  aparatu). Jedyny endpoint, który cokolwiek zmienia - patrz
  Uwierzytelnianie niżej.

Powyższe pięć endpointów `GET` nie wymaga uwierzytelniania - tylko
odczytują dane, dokładnie na tym poziomie, co osoba przeglądająca
program na poziomie **User**, bez żadnego PIN-u (patrz
[Co wolno na każdym poziomie](help://al_matrix)).

## Uwierzytelnianie

`POST /api/v1/commands` wymaga tokenu API poziomu **Operator albo
Engineer**, przesłanego w nagłówku HTTP:

```
Authorization: Bearer <token>
```

Istnieją dwa tokeny - jeden dla Operatora, jeden dla Inżyniera -
generowane automatycznie przy pierwszym uruchomieniu programu, na tej
samej zasadzie co PIN-y Operatora/Inżyniera (patrz
[Zmiana poziomu i wprowadzanie PIN-u](help://al_pin)): długa losowa
wartość, pokazana **dokładnie raz** w dzienniku startowym, po czym
przechowywany jest wyłącznie jej skrót, w
`epw_os/config/api_tokens.local.json` - pliku, który nigdy nie trafia
do repozytorium (tak jak `access.local.json`, plik z PIN-ami).
Zgubiony token? Usuń ten plik i uruchom program ponownie - oba tokeny
zostaną wygenerowane od nowa.

Zapytanie bez tokenu albo z tokenem, który się nie zgadza, jest
odrzucane (`401`) - **nie ma sposobu na wydanie komendy przez API bez
ważnego tokenu**, dokładnie zgodnie z zasadą GUI, że User nie steruje.
Tożsamość zapisywana w [Dzienniku audytowym](help://ea_audit_log) dla
każdej komendy wydanej tą drogą - i dla każdej nieudanej próby
uwierzytelnienia - to zawsze poziom, który token faktycznie udowodnił
(`API:Operator` / `API:Engineer`), nigdy nic, co zapytanie samo o
sobie twierdzi.

## Wystawienie poza ten komputer

`api_host` w pliku projektu decyduje, na czym API nasłuchuje -
`127.0.0.1` (domyślnie) oznacza, że dosięgnie go tylko ten komputer.
Ustawienie czegokolwiek innego (np. `0.0.0.0`) czyni je dostępnym z
sieci: każdy, kto dosięgnie portu, może odczytać każdy tag i alarm, a
każdy ze skradzionym lub odgadniętym tokenem Operatora/Inżyniera może
wydawać komendy. **Jeśli nie masz konkretnego powodu, żeby to zrobić,
nie rób tego** - API zaprojektowano pod integracje lokalne, nie jako
interfejs sterowania dostępny z sieci, i poza opisanym wyżej
sprawdzeniem tokenu nie ma żadnego dodatkowego zabezpieczenia sieciowego
(TLS, ograniczanie liczby zapytań).

Jeśli `api_host` zostanie kiedykolwiek ustawiony na coś innego niż ten
komputer, EPW OS wyraźnie o tym mówi, dwa razy: ostrzeżeniem w
dzienniku startowym oraz czerwonym wskaźnikiem na pasku statusu,
widocznym przez całą sesję (`⚠ API WYSTAWIONE: <host>`) - więc nigdy
nie jest to ciche, łatwe do przeoczenia ustawienie.
