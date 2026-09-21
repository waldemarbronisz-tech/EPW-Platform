# 7.3 Frame and Building

A frame is pure graphics illustrating a cabinet, a room or a zone - no terminals, no connections, no state, and no Aparat field. It has two variants: plain and building, plus an optional title placed at the top-left or centered along the top.

It is drawn by dragging a rectangle, the same way `graphics.rectangle` is - with one constraint: the minimum size is two grid cells in each direction; dragging a smaller rectangle still produces a minimum-size frame, never a zero-size one.
