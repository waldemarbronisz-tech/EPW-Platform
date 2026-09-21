# 3.1 Locations

A location is a SHORT PREFIX for a device id, not a device name. Examples of valid codes: `KOT` (boiler room), `BRAMA` (gate), `MAG` (warehouse), `OGROD` (garden). The code must be uppercase letters A-Z and digits 0-9 only (the `LOCATION_INVALID_CODE` rule in `DeviceValidation.ts`) - lowercase letters are rejected.

A device's location is DERIVED from the prefix of its id (the part before the first underscore), NOT stored as a separate field on the device. This has a concrete, practical consequence: moving a device to a different location is not an "edit" - the id is immutable once created ([4.2](help://synoptic/dev-naming)), so the only way is to DELETE the device and CREATE it again under the new id, with the same field values.

The location registry opens from the Aparaty menu > Rejestry projektu..., Lokalizacje tab. Adding one needs a code and a description; editing only lets you change the description - the code, once given, is just as immutable as a device id, for the same reason (it is already part of existing device ids).
