# 5.6 Net Validation: Mismatched Media, a Wire to Nowhere

Net validation runs on already-resolved nets (`validateNets` in `NetResolver.ts`), not on individual wires:

| Code | Severity | Meaning |
| --- | --- | --- |
| MIXED_MEDIUM | error | A net touches terminals of more than one medium - see [5.3](help://synoptic/sch-media). |
| DANGLING_NET | warning | A wire touches no terminal at all - "a wire to nowhere". |
| MULTIPLE_SOURCES | warning | Two or more SOURCE boundary points tied into one net - two supplies joined together. |

This is different from validating a single wire's own shape (e.g. no diagonal segments) - that is checked at the whole-schematic level on save (`validateProjectSchema` in `ProjectSchema.ts`), not at the net level.
