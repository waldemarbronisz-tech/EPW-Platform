# 3.2 I/O Cards

A card represents a physical I/O card on the controller: an id (e.g. `ELA1`), a model (a free-text description label), a channel kind (DI, DO, AI or AO - one card has exactly one kind) and a channel count. Channels are numbered starting from 1.

The card registry gives two things: (1) validating every channel address in the device form - does the card exist, does its kind match the kind used in the address, is the channel number within 1..channel_count (`validateChannelAddress`); (2) detecting the same channel assigned to two different devices at once (`CHANNEL_ADDRESS_COLLISION`) - the channel picker in the device form immediately greys out any channel already taken, showing by whom.

With no card in the registry at all, no valid channel address can be entered anywhere - every channel picker in the device form filters cards by the kind that field actually requires (e.g. a MEASURED device's `input` picker only ever shows AI cards).
