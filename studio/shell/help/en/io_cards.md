# I/O Cards

This controller's physical modules — and the **only** place where points
come into existence.

## One row = one module

| Column | Meaning |
|---|---|
| **Id** | the first segment of every address on this card (`ELA1` → `ELA1.DI.1`). No dot, no space |
| **Model** | the catalogue type of the module |
| **Channels (kind and count)** | tick the kinds the card has, and enter how many channels of each |
| **Modbus address** | 1–247, unique in the project; blank = the module is not addressed yet and **does not answer on the bus** |
| **Location** | where it sits; all of its points inherit it |
| **Responds** | in Live mode only: whether the controller is getting readings from it |

A card with **DI and AI** is **one row with two ticks**, not two rows.
One physical module has one address and one location, so splitting it
across two rows would mean entering those twice.

## Channel kinds

`DI` digital inputs, `DO` digital outputs, `AI` analog inputs, `AO`
analog outputs. An address is `id.KIND.number`, with no leading zeros.

## What happens when you add a card

The points appear immediately in the [Point Registry](help://points).
**Reducing the channel count deletes the surplus points together with
their descriptions** — with a warning. Removing a card removes all of
its points.

The same happens on the controller when the [project is
reloaded](help://controller): a card deleted in Studio takes its tags
with it.

## The Modbus bus

Below the table: **Transport** (RTU over a serial port, or TCP), then
the port, baud rate and parity for RTU, or the gateway address and TCP
port.

This is a **project** setting. Which controller physically uses Modbus
and which uses the simulator is a controller-local setting — visible in
[Controller Connection](help://controller).

## Locations

The **Add location** / **Remove location** buttons lead to the same list
as the [Locations](help://locations) branch — they are here because a
location is a field of a card, and this is usually the moment one turns
out to be missing.
