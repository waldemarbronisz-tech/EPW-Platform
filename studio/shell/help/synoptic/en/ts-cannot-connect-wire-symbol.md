# A Wire Will Not Connect to a Symbol

SYMPTOM: a wire ends near a symbol, but does not look connected (no junction dot, the net does not include the symbol).

CAUSE: a connection only forms from an EXACT touch of the terminal's grid point ([5.1](help://synoptic/sch-node-model)) - if the wire's end landed one pixel off, they do not touch geometrically at all, even though they look close visually.

FIX: make sure snap-to-grid is on (View > Snap to Grid), zoom in/out to land exactly on the visible terminal marker (shown on hovering the symbol), and end the wire drawing there.
