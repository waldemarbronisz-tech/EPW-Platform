# 3.3 Channel Addressing

A channel address has the format `CARD.KIND.CHANNEL`, for example `ELA1.DI.12` or `ADA1.DO.4`. Kind is one of DI (digital input), DO (digital output), AI (analog input), AO (analog output). Channel numbering starts at 1, not 0.

Whitespace around the whole address or around any of its three parts is ignored when comparing - `ELA1.DI.12` and ` ELA1 . DI . 12 ` are the same address for collision detection. Leading zeros do not matter either: `ELA1.DI.12` and `ELA1.DI.012` also count as the same single physical channel.

Inside the device form itself, an address is never typed by hand as text - the channel picker ([4.8](help://synoptic/dev-form-validation)) is three linked fields (a card, then the kind that follows from that card, then a channel number from that card's own 1..channel_count list), so a malformed format is practically impossible to enter through the interface. The plain text format matters when reading the project file by hand or from an external source.
