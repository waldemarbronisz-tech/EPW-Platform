# Device Status Panel

The panel on the right side of Main View shows the communication status
of four devices: Orange Pi (central unit), ELA-01 (input card), ADA-01
(output card), and Modbus RTU (bus).

Possible statuses: **ONLINE** (communication is fine), **OFFLINE**
(communication hasn't been established yet), and **COMM_FAILURE**
(communication was established but has been lost). See
[A Device Shows OFFLINE](help://ts_device_offline) if a status looks
wrong.

In the program's current configuration (simulation mode, no Modbus
hardware connected), these devices are simulated and normally show
ONLINE.
