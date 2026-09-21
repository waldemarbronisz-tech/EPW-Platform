# 5.3 Three Media: Electrical, Water, Ventilation

Every wire belongs to one of three media: ELECTRICAL, WATER, VENTILATION. A NEW wire's medium is chosen up front (keys `1`/`2`/`3`, or the toolbar toggle) - every wire drawn from then on inherits that choice until it is changed again. An already-drawn wire's medium can still be changed afterward in Properties.

A net touching terminals of more than one medium at once is a validation error (`MIXED_MEDIUM` in `NetResolver.ts`) - this applies to any pair of the three, not just power-water: power tied to ventilation is just as invalid as power tied to water.
