# Input stub, free wire end, label

Three different things that look alike at first glance ("something on the
diagram is not connected the usual way") — but they mean different things
and none of them can stand in for another.

## Input stub (Pin.disabled)

Deliberately excluding ONE input of a multi-input gate (AND/OR/NAND/NOR/
XOR/XNOR, two inputs or more) from that gate's own logic — a stubbed
input is treated as if it were not there at all, and the gate computes
its result from the rest. Available only on blocks that allow it
(multi-input gates) — stubbing an input on a block that does not support
it is a compile error, not something quietly ignored.

**A stub CANNOT be given a label** — it is not a wire end, it is the
absence of a wire at that point by definition.

## Free wire end

One end of a wire ([see the free-end section](help:concept_labels)) may
be left connected to no pin, with an optional text label documenting
where it was eventually meant to go. It is STILL a wire — its other end
really is connected to a pin — it is simply one end waiting to be
finished. Without a label the compiler reports an "Unfinished wire"
warning.

## Label

A text caption given to a free wire end. **A label joins NODES** (or
rather: is eventually meant to — see the caveat in [Labels, markers and
device bits](help:concept_labels)), whereas a stub is the absence of a
node to join at all. That is why a stub cannot be labelled: there is
nothing there to label.

## In short

| | Has a second, connected end? | Can it be labelled? | What the compiler does |
|---|---|---|---|
| Input stub | Not applicable (it is not a wire) | Not applicable | Nothing — the input is simply left out of the logic |
| Free end without a label | Yes | No | Warning: unfinished wire |
| Free end with a label | Yes | Yes | No warning (merging into a network node — planned, see above) |
