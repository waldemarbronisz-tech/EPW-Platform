# Moving a signal elsewhere on the diagram

Without drawing one long wire across the whole sheet — read [Labels,
markers and device bits](help:concept_labels) first for the full
comparison. Below are the two ways, both of which work:

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

## Through a wire label (no delay)

1. Draw a short wire from the pin that produces the signal and leave its
   other end **free**.
2. Give it a label (for example "READY").
3. Where the signal is needed, draw a second short wire into the
   receiving pin, also with a free end, and give it **the same** label
   (case does not matter).
4. Done — the compiler joins the two into one node, exactly as if they
   had been drawn as a single wire. No scan delay.

A label group must have exactly one source; it may have many receivers.
For when to choose a label and when a marker, see [Labels, markers and
device bits](help:concept_labels).
