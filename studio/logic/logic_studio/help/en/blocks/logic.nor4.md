The four-input form of [NOR](help:block:logic.nor): TRUE only when
**none** of the four inputs is TRUE.

### Example: silence in the switchgear

Four bay alarm bits -> one "NO ALARMS" lamp. The mirror image of the
[OR-4](help:block:logic.or4) example.

### Example 2: "nothing running" before service

`Pump 1 running` NOR `Pump 2 running` NOR `Stirrer running` NOR `Heater
running` -> permission to open the service hatch. While anything runs,
there is no permission.
