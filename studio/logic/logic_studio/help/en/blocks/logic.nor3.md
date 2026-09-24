The three-input form of [NOR](help:block:logic.nor): TRUE only when
**none** of the three inputs is TRUE.

### Example: "nothing in the way" readiness

`Door open` NOR `Drive fault` NOR `Service` -> `M.GOTOWY`. Every new
source of an interlock is one more input.

### Example 2: permission to close a gate

`Vehicle in the gateway` NOR `Movement in the zone` NOR `Service
interlock` -> permission for the automatic close. Any one of the
conditions removes the permission - exactly what an interlock should do.
