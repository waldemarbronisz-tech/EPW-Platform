# A Location or Card Cannot Be Deleted

SYMPTOM: the Delete button next to a location or card in Project Registries is disabled.

CAUSE: at least one device still uses that location (its code is the prefix of the device's id) or that card (one of its channel addresses points at it) - see [3.4](help://synoptic/reg-delete-protection). Hover the button to see the count and the devices' ids.

FIX: delete or move (i.e. recreate under a different id - [3.1](help://synoptic/reg-locations)) every listed device before deleting the location or card.
