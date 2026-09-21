# 4.2 Naming Convention

Every device has three separate text fields, each with a different role:

| Field | Role | Example |
| --- | --- | --- |
| id | The machine key, IMMUTABLE once created | `KOT_KMG1` |
| designation | What is shown on the diagram | `-K1` |
| name | A human-readable description | "Boiler heater contactor" |

The rule is simple: A HUMAN sees the designation (on the symbol, in tables), THE MACHINE sees the id (addresses, screen references). The id must be uppercase letters, digits and exactly one underscore, where the part before the underscore is a registered location's code (`validateDeviceId`) - so `KOT_KMG1` reads as "device KMG1 in location KOT".

The id is immutable because it is a key: a screen element points at a device BY its id ([4.1](help://synoptic/dev-why-not-in-screen)), and a device's location is derived from it ([3.1](help://synoptic/reg-locations)). The device form directly disables editing the Id field once an existing device is being edited - it is only active when creating a new one.

Duplicating a device (the Duplikuj button in the list) clears ONLY the id and the designation in the new draft - the name, behavior and every detailed field (e.g. channel addresses) are carried over unchanged, so they must be deliberately corrected (at minimum the channel addresses, which would otherwise collide with the original).
