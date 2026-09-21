# 10.1 What the Project File Contains

The project file (`.epwsyn`, JSON) has a `format: "EPW_SYNOPTIC"` field and a `schema_version`. It contains: project metadata, canvas configuration, `objects` and `connections` arrays, and optionally `meters`, `signalPanels`, `frames`, `devices`, `locations`, `cards`, `kind` (the screen kind - always SCHEMATIC today, see [1.4](help://synoptic/intro-screens)) and `helpLanguage` (the help language).

Every optional field was added the same way: appended as a new field without bumping the schema version, because an older file simply has none of it and loads with a sensible default (an empty array/map, Polish) instead of an error.

> **Note:** A SECOND, independent format called EPW_PROJECT also exists in this repository (`ProjectV2Schema.ts`), with a completely different model (multiple screens in one file, port-based rather than node-based connections). Nothing in the running editor writes or reads it today - it is type definitions and a validator only, groundwork for a future architecture, not an active format.
