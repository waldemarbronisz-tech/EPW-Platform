# 4.1 Why Device Configuration Does Not Live in the Screen

In this editor a device is defined ONCE, in the project's shared list (Aparaty > Lista aparatow...). A screen element (a schematic symbol, a meter row, a signal panel row) never stores the device's configuration - it only says "at this spot, with this symbol, show device KOT_KMG1", through a field holding its id.

The same device shown on many symbols, or even on many screens, is the GOAL of this architecture, not a bug to catch. Selecting two different symbols that point at the same device id reports no error at all ([6.4](help://synoptic/sym-device-binding)) - that is a normal, valid state.

Internally: `SynopticObject.deviceId` (a symbol), `MeterElementRow.device` (a meter row) and the matching field on a signal panel row are always just an ID STRING, never a copy of the device's own fields. A meter's unit and format ([7.1](help://synoptic/elem-meter)) are always read from the device at display time, never copied onto the row - changing the unit on the device instantly changes what every row pointing at it shows.
