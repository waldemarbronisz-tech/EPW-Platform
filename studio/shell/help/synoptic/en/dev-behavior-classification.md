# 4.3 Classification by Behavior, Not by Device Kind

A device is classified by BEHAVIOR, not by device kind. The `kind` field (e.g. "contactor", "valve", "sensor") is ONLY a descriptive label with no functional meaning - it affects no validation rule and none of the device's fields. What fields, signals and commands a device has is decided entirely by the `behavior` field.

There are exactly four behaviors, and nothing else may be silently added: SWITCHED ([4.4](help://synoptic/dev-switched)), SIGNAL ([4.5](help://synoptic/dev-signal)), MEASURED ([4.6](help://synoptic/dev-measured)), MODULATED ([4.7](help://synoptic/dev-modulated)). Choosing a behavior in the form changes the whole lower section of it - and if the device already had detail fields filled in for a different behavior, changing it asks for confirmation, because it will clear them.
