# The scan cycle and the one-scan delay

## Execution order

The engine evaluates every block on the diagram in ONE fixed order per
scan — not the order they were drawn in, but the order that follows from
WHO depends on WHOM (topological order): source blocks first (physical
inputs, markers, constants), then everything that depends on them, in an
order such that by the time a block is evaluated, every block feeding its
inputs has already been evaluated in THE SAME scan.

## Where z⁻¹ comes from

Two things in this program deliberately break that "the input was already
evaluated this scan" rule:

1. **A feedback loop through a stateful block** (an SR/RS latch, a timer,
   a counter, an analog hysteresis...) — by definition it cannot be put
   in topological order, because the block depends indirectly on itself.
   The resolution: a stateful block in such a loop presents the value of
   ITS OWN STATE from before this evaluation, not a result computed on
   the spot — that is, the value "from the previous scan".
2. **Markers** (internal bits/registers, M./MR./MW.) — a write is
   buffered and committed only AFTER every block in the scan has been
   evaluated (see [Labels, markers and device
   bits](help:concept_labels)). A block reading a marker written by
   another block in THE SAME scan always sees the value from before that
   write.

Both cases are called a "one-scan delay" or, in the classic language of
control engineering, **z⁻¹** — the value something sees corresponds to
the state one full pass of the engine ago, not to the state "live".

## How to read it on a diagram

There is no separate z⁻¹ symbol on the sheet today — the delay follows
purely from USING a stateful block or a marker at that point, not from
some distinct element. If your logic depends on two values being seen in
THE SAME scan, avoid routing either of them through a marker or through a
stateful block in a feedback loop.
