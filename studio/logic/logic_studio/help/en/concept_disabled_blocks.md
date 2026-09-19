# Disabled blocks and forces

## What a disabled block means

A block can be disabled (from the selection menu, or with a shortcut if
one is bound) — a disabled block is skipped during project validation, as
if it did not logically exist for the time being, while remaining visible
on the diagram. Useful for switching a piece of logic off temporarily
without deleting it and without tearing up wires that would then have to
be redrawn by hand.

A disabled block is marked CLEARLY on the canvas (it looks different from
an active one) — deliberately hard to miss, so that nobody overlooks the
fact that part of the logic on the sheet is inactive.

## What the flag does in the export

The disabled state is part of the exported runtime — EPW-OS knows the
block is to be skipped, in exactly the same way the editor and the
simulation do. Disabling a block in Logic Studio is therefore not a
cosmetic operation on the drawing: it genuinely changes what ends up
running on the plant.

## Forces

During simulation, physical inputs/outputs (DI/DO) and internal bits can
be given a forced value (FORCE TRUE/FORCE FALSE) regardless of what the
simulated hardware or the computed logic actually produces — set from the
property panel of the selected block while the simulation runs. A force
is runtime state ONLY: it is never written to the project file or to the
exported runtime, so a force set while testing on the bench cannot
accidentally travel with the project to site and force something on real
hardware.
