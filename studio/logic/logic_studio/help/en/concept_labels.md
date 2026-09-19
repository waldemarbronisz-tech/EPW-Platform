# Labels, markers and device bits

Three different ways to take a value computed in one place on a diagram
and use it somewhere else, without drawing one long wire across the whole
sheet. They are easy to confuse — here is the rule for choosing, and what
actually sets them apart.

| Way | What it is | One-scan delay |
|---|---|---|
| **Device bit** (DI/DO/AI/AO) | A physical signal on a particular ELA/ADA module | Not applicable — read/written straight from/to the hardware |
| **Marker** (internal bit or register, M./MR./MW.) | The project's own internal memory, tied to no physical terminal | **Yes, it can happen** |
| **Wire label** | A text name given to a free wire end | Eventually: no — see the caveat below |

## Marker: why it can cost you a scan

A write to a marker (the "Bit output (internal)" / "Register output
(internal)" blocks) does not reach memory immediately — the engine
buffers every write made during a scan and commits them only AFTER every
block in that scan has been evaluated. So if block A writes a marker and
block B reads it in the SAME scan, block B sees the value from BEFORE
A's write — it sees the new value only on the NEXT scan. That is exactly
the z⁻¹ delay described separately in [The scan cycle and the one-scan
delay](help:concept_scan_cycle). Where the blocks sit on the sheet
(whether A is "before" or "after" B) makes no difference here — all that
matters is that the write and the read are separated by a scan boundary.

## Wire label: how it stands today

A wire may have one **free** end (connected to no pin) and carry a text
label — this suppresses the compiler's "Unfinished wire" warning and
documents where that end was meant to go. **Merging two wires with the
same label into one network node (so that the label actually CARRIES the
signal, with no wire drawn) is a planned, not yet implemented part of
this mechanism** — today a label is documentation metadata, not a working
way to move a signal. Until that exists, the only WORKING way to move a
signal without drawing a wire across the sheet is a marker (see [Moving a
signal elsewhere on the diagram](help:guide_move_signal)).

## The rule for choosing

- A physical signal (a real input/output on a module) → a device bit,
  always.
- A helper signal needed in several places on the sheet, where one scan
  of delay is acceptable (it usually is — it only ever affects the
  relationship between two particular blocks within the same scan) → a
  marker.
- A stub on a wire you are about to connect → a free end with no label
  (see [Input stub, free wire end, label](help:concept_stubs) — that is a
  THIRD, separate thing, however similar it looks).
