# A first diagram: input, gate, output

The shortest route to seeing working logic on screen.

1. **Add a digital input.** Find [DI](help:block:input.di) in the block
   library (the "Inputs / Outputs" category) and drag it onto the canvas.
2. **Add a logic gate.** Drag, say, [NOT](help:block:logic.not) from the
   "Logic gates" category next to the input.
3. **Add a digital output.** Drag [DO](help:block:output.do) in.
4. **Wire them together.** Click and drag from one block's output pin to
   the next block's input pin: DI → NOT → DO.
5. **Set the addresses.** Select the DI and set its `Address` in the
   property panel (for example "ELA01.DI.1"); do the same for the DO.
6. **Compile** (F5) — check that there are no errors.
7. **Run the simulation** and toggle the input — watch the output follow.
   The details are in [Running a simulation and checking what the logic
   does](help:guide_simulation).

Whenever you are unsure what a block along the way does, select it and
press **F1**.
