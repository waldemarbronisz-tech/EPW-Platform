# 5.5 The Junction Dot - When It Appears

A junction dot appears at every grid point where THREE OR MORE branches meet - three or more wire segments, or two segments plus a symbol terminal (`getJunctionPoints` in `NetResolver.ts`).

An ordinary bend in the same wire (its own two segments meeting at one point) is NOT a junction - it is just a corner, counting as two branches, not three. A point in the MIDDLE of one segment's length (e.g. a tap off a busbar - [5.4](help://synoptic/sch-wire-style)) counts as TWO branches of that one segment (because it conceptually splits it in two), so a tap plus that midpoint together make three - and that is where the dot appears.
