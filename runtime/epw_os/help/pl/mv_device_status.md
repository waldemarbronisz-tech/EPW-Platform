# Panel statusu urządzeń

Panel po prawej stronie Main View pokazuje status komunikacji z czterema
urządzeniami: Orange Pi (jednostka centralna), ELA-01 (karta wejść),
ADA-01 (karta wyjść) i Modbus RTU (magistrala).

Możliwe statusy: **ONLINE** (komunikacja prawidłowa), **OFFLINE**
(jeszcze nie nawiązano łączności) i **COMM_FAILURE** (łączność była, ale
została utracona). Zobacz [Urządzenie pokazuje OFFLINE](help://ts_device_offline),
jeśli status budzi wątpliwości.

W obecnej konfiguracji programu (tryb symulacji, bez podłączonego
sprzętu Modbus) urządzenia te są symulowane i zwykle pokazują ONLINE.
