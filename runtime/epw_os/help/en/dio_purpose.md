# What These Pages Are For

**Digital Inputs** shows the state of 64 digital inputs (DI1–DI64) —
signals received from the installation (e.g. limit switch state,
external signaling).

**Control Outputs** shows 64 digital outputs (DO01–DO64) — signals sent
to the installation (e.g. controlling a contactor). The first four
outputs (DO01–DO04) have real feedback wired from inputs DI1–DI4 — the
state shown on screen comes from that feedback signal, not from the
command itself. The rest of the outputs (DO05–DO64) are self-contained
— their own tag serves as both the command and the feedback.

Both pages share the same layout: address (a PLC-style label —
informational only, %IX0.N / %QX0.N), tag, description, state, an LED
indicator, and a timestamp of the last change.
