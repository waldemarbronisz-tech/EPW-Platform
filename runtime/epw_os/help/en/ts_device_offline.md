# A Device Shows OFFLINE

The device status panel on Main View (see
[Device Status Panel](help://mv_device_status)) shows one of three
statuses:

- **OFFLINE** — the program hasn't established any communication with
  this device since it started (a normal state right at the beginning,
  before the first data arrives).
- **ONLINE** — communication is working fine.
- **COMM_FAILURE** — communication WAS working, but has been lost (the
  device stopped responding within the expected time).

If the status stays OFFLINE longer than it should, or switches to
COMM_FAILURE:

1. Check the Alarms panel — a device communication failure raises a
   separate alarm there, naming the device.
2. In simulation mode (no hardware connected), devices are simulated in
   software and should quickly turn ONLINE on their own — a long-lasting
   OFFLINE in this mode may just mean the program is still starting up.
3. In live mode, check the physical connection to that device.

See also: [Where Alarms Come From](help://alm_source).
