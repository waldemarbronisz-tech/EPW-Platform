The three-input form of [AND](help:block:logic.and): the output is TRUE
only when **all three** inputs are TRUE. Truth table and rules as for the
two-input AND.

### Example: drive permission

`Supply OK` AND `No fault` AND `Guard closed` -> `M.NAPED_ZEZW`. Should a
fourth condition appear one day, swap the block for
[AND-4](help:block:logic.and4) - the wires stay, one input is added. For
more than four, cascade two gates (the first's output into the second)
or wrap the conditions in a [macro](help:concept_macros).
