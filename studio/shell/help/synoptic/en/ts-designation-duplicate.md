# A Device Cannot Be Saved - Duplicate Designation

SYMPTOM: saving a device shows an error about a duplicate designation within a location.

CAUSE: two devices in the SAME location cannot share a designation (`DEVICE_DUPLICATE_DESIGNATION_IN_LOCATION`) - the same designation in TWO DIFFERENT locations is, however, perfectly allowed.

FIX: change one of the two devices' designations to something unique within that location.
