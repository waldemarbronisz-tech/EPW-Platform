# 3.4 Why Deleting a Location or Card in Use Is Blocked

Deleting a location whose code is the prefix of even one existing device's id is blocked - its Delete button is disabled, and hovering it shows how many devices use it.

Likewise, deleting a card with even one channel referenced by any device's address is blocked - for the same reason: deleting the card would leave those devices with addresses pointing at a card that no longer exists.

This is not an interface restriction added "just in case" - it is a direct consequence of how a device id and a channel address are built (see [3.1](help://synoptic/reg-locations) and [3.3](help://synoptic/reg-addressing)): deleting a location or card still in use would leave the data in a state `validateDeviceRegistry` could no longer call valid.
