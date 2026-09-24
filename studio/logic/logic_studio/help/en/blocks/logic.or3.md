The three-input form of [OR](help:block:logic.or): TRUE when **any** of
the three inputs is TRUE.

### Example: stop from three sources

`STOP panel` OR `STOP remote` OR `Limit switch` -> the R input of the
latch holding the drive. Note: a STOP button is often a normally-closed
contact (NC) - then feed the gate its negation ([NOT](help:block:logic.not)),
so the OR counts "pressed", not "released".
