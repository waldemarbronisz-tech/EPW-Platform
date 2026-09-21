# 10.2 Schema Versioning and Migrations

`CURRENT_SCHEMA_VERSION` (in `ProjectSchema.ts`) only increases on a backward-incompatible change - e.g. moving from the port-based connection model to the node-based one bumped it from 1 to 2. Every such change has its own migration (`Migrations.ts`) that reshapes an older file into the current shape on load.

A file with a version number HIGHER than the current editor build supports is rejected outright, with an error - it is never partially loaded or loaded "best-effort".
