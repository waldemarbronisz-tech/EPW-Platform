# The Device Id Cannot Be Changed

SYMPTOM: when editing an existing device, the Id field is greyed out and cannot be changed.

CAUSE: the id is DELIBERATELY immutable - it is the key screen symbols and meter/panel rows reference the device by ([4.2](help://synoptic/dev-naming)). Editing it live would break every such reference.

FIX: create a new device with the desired id, copy the old one's field values into it by hand (Duplikuj only clears id/designation, so it can help as a starting point), then delete the old device. Every symbol pointing at the old id will need to be re-pointed at the new one by hand - deleting a device does not warn how many screen symbols reference it.
