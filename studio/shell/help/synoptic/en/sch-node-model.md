# 5.1 The Node-Based Connection Model

A schematic wire is a freely drawn orthogonal polyline (horizontal and vertical segments only) - NOT a pair of ports. Two wires, or a wire and a symbol terminal, belong to the SAME electrical/water/ventilation net purely because they touch GEOMETRICALLY - at the same grid point.

A touch can be at the MIDDLE of another wire's segment, not only at its end - that is exactly what makes a busbar work ([5.4](help://synoptic/sch-wire-style)): every wire touching any point along its length belongs to the same net.

Having no ports simplifies editing: a symbol's terminal can move (by resizing it - [6.2](help://synoptic/sym-terminals)) or a wire's node can be dragged, and the connection EXISTS as long as the points actually touch, with no separate "link" to repair or lose. The net is recomputed from geometry alone (`resolveNets` in `NetResolver.ts`), never stored explicitly in the project file.
