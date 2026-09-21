# 2.4 A Complete Example From Scratch

A complete example: a circuit from a supply point (a boundary point) through a busbar to two loads (two contactors controlling lighting). Step by step, with concrete values.

## Step 1 - registries

1. Menu Aparaty > Rejestry projektu... > Lokalizacje tab: add code `MAG` (description "Warehouse").
2. Karty tab: add card `ELA1` (any model, kind DI, 16 channels) and card `ADA1` (kind DO, 16 channels).

## Step 2 - two SWITCHED devices

1. Menu Aparaty > Lista aparatow... > + Dodaj. Id: location `MAG`, suffix `OSW1`. Designation `-K1`, name "Shelf lighting 1". Behavior SWITCHED, feedback mode DUAL, diClosed `ELA1.DI.1`, diOpen `ELA1.DI.2`. Command: 1 output, style MAINTAINED, doClose `ADA1.DO.1`. Save.
2. Repeat for the second load: suffix `OSW2`, designation `-K2`, diClosed `ELA1.DI.3`, diOpen `ELA1.DI.4`, doClose `ADA1.DO.2`.

## Step 3 - the schematic screen

1. Drag a Boundary Point symbol from the library onto the canvas. In Properties, set Boundary Direction to SOURCE and Boundary Medium to ELECTRICAL.
2. Select medium 1 (Electrical, key `1`) and draw a wire from the boundary point's terminal to where the busbar will start.
3. Set the NEW wire's style to Bus (the toggle in the top toolbar) and draw a short, horizontal busbar segment.
4. Drag two Circuit Breaker (or Disconnect Switch) symbols near the busbar. Draw one wire from each, ending EXACTLY on any point along the busbar's length (not only at its end) - see [5.4](help://synoptic/sch-wire-style).
5. Select each of the two symbols and, in Properties, in the Aparat field, choose `MAG_OSW1` and `MAG_OSW2` respectively.

Result: both branches count as ONE electrical net (because they touch the same busbar geometrically - see [5.1](help://synoptic/sch-node-model)), and each symbol shows its own device's designation (auto-filled the moment it was assigned - see [6.4](help://synoptic/sym-device-binding)).
