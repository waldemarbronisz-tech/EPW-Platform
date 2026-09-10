# Device Composition

The registry of physical I/O modules: ELA (digital), ADA (analog/
protection), EPM and similar. For each module:

- **Id** — the logical address you assign (e.g. `ELA1`) — it becomes
  the prefix for that module's point addresses (`ELA1.DI.1`,
  `ELA1.DI.2`, ...).
- **Model** — the physical description/designation (e.g. `ELA01`).
- **Kind** — DI / DO / AI / AO — which channel type this module has.
- **Channels** — how many channels of that kind the module provides.
- **Modbus Address** — the device's unit id (1–247) on the Modbus bus
  the controller (Orange Pi) uses to talk to the modules.

**Adding a card automatically creates its points** in the Point
Registry — you never type them by hand. Changing the kind/channel count
regenerates them, keeping any descriptions already typed in.

At the bottom of the panel: **Modbus Bus** — one shared setting for
every module: RTU (serial port, baud rate, parity) or TCP (gateway
address, port). This is how the controller talks to the modules at
all — saved in the project today, ready for a future runtime Modbus
driver (not implemented yet).
