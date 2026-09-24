The three-input form of [NAND](help:block:logic.nand): FALSE only when
**all three** inputs are TRUE, otherwise TRUE.

### Example: limiting the number of running loads

Three heaters on one circuit - the third may not switch on while two
already heat: `Heater 1` NAND `Heater 2` NAND `Heater 3` is FALSE only
with all three at once; use it as the interlock on the third heater's
permission AND.
