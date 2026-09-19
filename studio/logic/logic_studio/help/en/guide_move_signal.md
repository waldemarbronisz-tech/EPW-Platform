# Moving a signal elsewhere on the diagram

Without drawing one long wire across the whole sheet — read [Labels,
markers and device bits](help:concept_labels) first for the full
comparison. Below is the way that **works today**:

## Through a marker (an internal bit or register)

1. Where the signal is PRODUCED, add a "Bit output (internal)" block (or
   "Register output (internal)" for an analog value) and wire the result
   into it.
2. Click that block's `Bit` property and pick or create a name for the
   internal signal (for example "M_READY").
3. Where the signal is NEEDED — however far away on the sheet, or in an
   entirely different bay — add a "Bit input (internal)" block (or
   "Register input (internal)") and select THE SAME name in its `Bit`
   property.
4. Done — both copies read and write the same internal signal, with no
   wire between them on the diagram.

Keep in mind the possible one-scan delay between writing and reading the
same marker within one scan — see [The scan cycle and the one-scan
delay](help:concept_scan_cycle).

## Wire labels — not all the way there yet

A labelled free wire end (see [Input stub, free wire end,
label](help:concept_stubs)) today only documents where the wire was meant
to go — it does not carry the signal yet. Once merging labels into
network nodes is finished, this guide will be updated with the shorter
way that follows from it.
