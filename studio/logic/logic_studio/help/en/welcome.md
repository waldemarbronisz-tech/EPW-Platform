# Welcome to EPW Logic Studio {version}

EPW Logic Studio is a logic diagram editor for designing and simulating
control logic that is then exported to run in EPW-OS. You draw a diagram
of blocks (inputs, gates, timers, latches, counters, outputs), check it
in a simulation on the same canvas, and the compiled program travels to
the controller with the Studio project.

Start with [A first diagram](help:guide_first_diagram), or go straight to
the **Block catalog** in the tree on the left to see what is available
(the [AND](help:block:logic.and) gate, say).

If something on the diagram looks familiar but you are not sure what it
does - select it and press **F1**: help opens on the right description.

## Contents

- **Concepts** - things that are easy to confuse (labels versus markers,
  a stub versus a free wire end, the one-scan delay) and the block
  families: [gates](help:concept_gates), [timers](help:concept_timers),
  [latches and edges](help:concept_memory_edges),
  [counters](help:concept_counters).
- **Guides** - step by step: a first diagram, moving a signal, the
  simulation, the export, macro blocks, [typical control
  circuits](help:guide_typical_circuits) with ready connections.
- **Block catalog** - the complete, always current description of every
  block in the library: pins, properties, defaults. The pages of gates,
  timers, latches, edges and counters also carry a **truth table**, an
  **animation** of the diagram in simulation and **examples of use**.
- **Keyboard shortcuts** - the currently registered shortcuts.

## How to read the animations in the Block catalog

An animation is a real diagram from this editor, computed by the same
engine the simulation uses: a **green** wire or port is TRUE, a **black**
one FALSE; the DI inputs on the left are toggled by "the operator", the
DO output on the right shows the result. It is exactly the picture you
will see on your own diagram after pressing Start in the simulation.

## One help for the whole Studio

The same topics are available in EPW Studio (F1 in the Logic department)
next to the help of the registers, the screens and the controller -
cross-references between departments work both ways.
