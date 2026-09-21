# The Meter Wizard Shows an Empty List

SYMPTOM: the meter wizard (the Kreator... button on a Meter element) shows an empty list instead of devices to choose from.

CAUSE: the wizard shows ONLY devices with the MEASURED behavior ([4.6](help://synoptic/dev-measured)) - if the project has no such device yet (or existing ones have a different behavior), the list is empty.

FIX: Aparaty > Lista aparatow... > + Dodaj, set Behavior to MEASURED, fill it in and save. Close and reopen the wizard to see the newly added device.
