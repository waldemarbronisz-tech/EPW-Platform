# 6.2 Terminals Are Always at the Middle of an Edge

A symbol's terminal always sits exactly at the middle of one of the four edges (top, bottom, left, right) of the object - the symbol registry only ever declares WHICH edge, never a raw x/y position. The actual position is computed from the object's current width and height (`getObjectTerminals` in `Terminals.ts`) whenever it is needed, never stored fixed.

Practical consequence: when a symbol is resized (e.g. a valve stretched to fit an existing pipe run), its terminal FOLLOWS the new edge midpoint automatically - it does not stay pinned where it was at the default size. The exception is the boundary point ([5.7](help://synoptic/sch-boundary-point)), whose single terminal depends on its Boundary Port Side field, not on its size.
