# 6.1 Library and Categories

The symbol library (the Object Library panel) is split into categories: Electrical, Water, HVAC, Instrumentation, SCADA and others - every symbol belongs to exactly one. Dragging a symbol from the library onto the canvas creates a new schematic object.

Every symbol has its own definition (type, label, default size, allowed states, terminals) in the symbol registry - the one place that decides what a given symbol type can do at all. A few symbols are flagged as hidden from the library (they still work correctly if they already exist in an open project), which changes nothing about how they are used - only whether they show up in the panel to be dragged.
