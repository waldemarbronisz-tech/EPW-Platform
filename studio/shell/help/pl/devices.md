# Skład urządzenia

Lista funkcjonalnych modułów tego sterownika - Alarmówka, Zabezpieczenia
elektryczne, Trendy i tak dalej - PRZEPISANA z realnego mechanizmu
runtime (`epw_os/core/feature_config.py`), nie wymyślona na potrzeby
Studio.

**To nie jest lista przełączników "włącz/wyłącz funkcję tymczasowo".**
To skład urządzenia, ustalany raz, przy zakładaniu projektu - sterownik
podlewania **nie ma** alarmówki, tak samo jak nie ma jej termostat, nie
jako "wyłączona", tylko jako fakt o tym, z czego to urządzenie się
składa.

Każdy wiersz: nazwa, opis jednym zdaniem, i przełącznik dwustanowy
[0][I] ze słownym stanem TAK/NIE obok (żeby stan było widać, nie tylko
domyślać się z ikony).

**Moduł spoza składu znika z drzewa projektu CAŁKOWICIE** - gałąź
Alarmówki czy Zabezpieczeń elektrycznych po prostu nie istnieje,
dopóki nie zaznaczysz tego modułu tutaj. Wyłączenie modułu, który ma
już dane (np. skonfigurowane strefy), pyta wprost o potwierdzenie -
dane nigdy nie są kasowane, tylko chowane; ponowne włączenie modułu
przywraca je bez zmian.

Kilka pozycji na liście (Trendy, Jakość zasilania, Diagnostyka
magistrali...) odpowiada realnym funkcjom runtime, dla których Studio
nie ma jeszcze własnego panelu konfiguracji - zaznaczenie ich zapisuje
się w projekcie uczciwie, po prostu jeszcze bez widocznego efektu w
drzewie.
