# A Wire Does Not Join the Busbar

SYMPTOM: a new wire runs near the busbar, but does not count as part of its net.

CAUSE: the touch must land EXACTLY on the busbar's segment (any point along its length, but it must lie on it geometrically), not merely close to it - see [5.4](help://synoptic/sch-wire-style).

FIX: zoom in around the busbar, make sure snap-to-grid is on, and end (or start) the wire exactly on a point lying on the busbar's line.
