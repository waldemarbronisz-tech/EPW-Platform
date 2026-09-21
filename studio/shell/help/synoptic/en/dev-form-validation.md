# 4.8 The Device Form and Live Validation

The device form validates LIVE, on every field change, through `validateDeviceRegistry` (the only place any rule is actually decided) - every error appears immediately under the field it is about, and the Save button stays disabled while even one error exists.

The channel address picker greys out any channel another device already occupies, showing its id in parentheses - which makes a channel collision practically impossible to enter by accident, even though `CHANNEL_ADDRESS_COLLISION` still formally exists as a rule checked at save time.

The Id field is only editable when creating a new device (a location dropdown plus a free suffix) and is disabled when editing an existing one - the reason is in [4.2](help://synoptic/dev-naming).
