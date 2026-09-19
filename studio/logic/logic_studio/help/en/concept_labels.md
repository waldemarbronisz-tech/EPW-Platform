# Labels, markers and device bits

Three different ways to take a value computed in one place on a diagram
and use it somewhere else, without drawing one long wire across the whole
sheet. They are easy to confuse — here is the rule for choosing, and what
actually sets them apart.

| Way | What it is | One-scan delay |
|---|---|---|
| **Device bit** (DI/DO/AI/AO) | A physical signal on a particular ELA/ADA module | Not applicable — read/written straight from/to the hardware |
| **Marker** (internal bit or register, M./MR./MW.) | The project's own internal memory, tied to no physical terminal | **Yes, it can happen** |
| **Wire label** | A text name on a wire; wires sharing a label are one node | No — it is an ordinary connection |

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

## Wire label: how it works

Wires carrying **the same label are one network node**, wherever they sit
on the sheet — the compiler joins them with exactly the same pin
connection a hand-drawn wire goes through, so from there on (execution
order, simulation, export) a labelled network and a drawn one are
indistinguishable. Label comparison **ignores case** ("Interlock BB" and
"interlock bb" name the same node).

The rules that follow from it:

- a label group must have **exactly one source** (an output pin); no
  source, or two sources, is a compile error;
- a group with a source but no receiver gives a "signal is not received
  anywhere" warning;
- a free end **without** a label gives an "unfinished wire" warning.

A label costs no scan delay — unlike a marker, it is an ordinary
connection, just without a wire drawn across the whole sheet.

## The rule for choosing

- A physical signal (a real input/output on a module) → a device bit,
  always.
- A helper signal needed in several places on THE SAME sheet, with no
  delay → a wire label.
- A helper signal where one scan of delay is acceptable (it usually is —
  it only ever affects the relationship between two particular blocks
  within the same scan), or a value that should be named and visible in
  the signal registry → a marker.
- A stub on a wire you are about to connect → a free end with no label
  (see [Input stub, free wire end, label](help:concept_stubs) — that is a
  THIRD, separate thing, however similar it looks).
