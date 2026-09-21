# 2.2 Working Order: Registries First, Then Devices, Then the Screen

The practical order for a new SCHEMATIC project is: registries FIRST (locations and cards, chapter 3), THEN devices (chapter 4), and ONLY THEN symbols on the screen (chapter 6).

The reason is right in the data contract: a device id MUST start with an already-existing location's code (`validateDeviceId` in `DeviceValidation.ts`), and every channel address MUST point at an already-existing card (`validateChannelAddress`). The device form enforces this directly: when creating a new device, the Id field is a dropdown of locations, not free text - if that list is empty, adding a device is blocked with a hint to add a location in Project Registries first.

A symbol on the schematic screen does not create a device - it only points at one that already exists, through the Aparat dropdown in Properties ([6.4](help://synoptic/sym-device-binding)). Placing a symbol before any devices exist simply leaves it unassigned (a valid state - see [4.1](help://synoptic/dev-why-not-in-screen)) until a device is created for it to point at.
