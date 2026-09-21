# 5.4 Wire Style: Normal and Busbar

Every wire has one of two styles: NORMAL or BUS (busbar/manifold). A busbar is NOT a separate symbol or a separate networking mechanism - it is the same wire, drawn thicker, to visually flag that it is meant to have many loads tapped along its whole length. A water manifold is exactly the same thing, just in the WATER medium.

The "tap in at any point along the length" mechanism is not actually limited to the BUS style at all - any wire, regardless of style, joins another wire by touching it in the MIDDLE of a segment, not only at an end (see [5.1](help://synoptic/sch-node-model)). The BUS style is purely a visual signal of that intent, not a condition for it working.

A NEW wire's style is chosen up front in the toolbar (next to the medium choice), the same way medium is - an already-drawn wire can still be switched afterward in Properties.
