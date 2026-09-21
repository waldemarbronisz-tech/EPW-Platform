# The Save Button in the Device Form Is Disabled

SYMPTOM: the Save button in the device form is disabled and does not respond to clicking.

CAUSE: at least one field still has an active validation error ([4.8](help://synoptic/dev-form-validation)) - Save stays disabled until all of them are gone.

FIX: scroll the form and find every red text under a field - there is usually more than one at once on a freshly created device.
