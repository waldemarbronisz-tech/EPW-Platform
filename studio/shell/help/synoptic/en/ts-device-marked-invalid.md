# A Device Is Marked With an Error in the List

SYMPTOM: a device's row in the Device List is shown in the alarm color.

CAUSE: `validateDeviceRegistry` found at least one error for that device - hover the row to see the exact error text in its tooltip.

FIX: open the device for editing (Edytuj) - every error also appears directly under the field it is about ([4.8](help://synoptic/dev-form-validation)), with the same text as the list's tooltip.
