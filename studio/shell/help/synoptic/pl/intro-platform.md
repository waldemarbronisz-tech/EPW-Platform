# 1.2 Miejsce w platformie EPW

Platforma EPW sklada sie z trzech osobnych aplikacji, kazda w swoim wlasnym repozytorium:

- EPW-OS - aplikacja uruchomieniowa. Wyswietla ekrany, odczytuje i zapisuje sygnaly na prawdziwym sprzecie, obsluguje alarmy, poziomy dostepu, historie.
- EPW-Logic-Studio - buduje automatyke: regoly sterowania, blokady, sekwencje. To tam definiuje sie np. prog ostrzegawczy licznika przelaczen (zobacz [4.4](help://synoptic/dev-switched)).
- EPW-Synoptic-Editor (ten program) - tworzy grafike ekranu i liste aparatow, ktore EPW-OS potem wyswietla i EPW-Logic-Studio wykorzystuje w regulach.

W dokumentacji EPW-OS (pliki `epw_os/gui/widgets/synoptic_runtime.py`, `epw_os/gui/main_window.py`) pojawia sie wzmianka o Home Assistant jako warstwie DODATKOWEJ - kazdy aparat SWITCHED/SIGNAL/MEASURED/MODULATED ma pole `publishToHa`, ktore mowi, czy jego stan ma trafic tez do Home Assistant jako encja. Home Assistant nie jest jednak torem sterowania: nic w tym edytorze ani w kontrakcie DeviceSchema nie zaklada, ze polecenie moze przyjsc STAMTAD z powrotem do sterownika - to wygoda podgladu/powiadomien, nie kanal komend.

> **Uwaga:** Rozbieznosc znaleziona podczas pisania tej pomocy: EPW-Logic-Studio, wymienione w tresci tego zadania jako aplikacja majaca juz wlasny system pomocy w stylu Windows 98, w rzeczywistosci go NIE MA (sprawdzone w kodzie repozytorium) - tylko EPW-OS go posiada. Ten fakt zglaszany jest w raporcie ukonczenia zadania.
