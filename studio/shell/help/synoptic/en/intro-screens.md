# 1.4 Screen Kind and the kind Field

Every project is a SCHEMATIC screen: symbols, wires, meters, signal panels (chapter [5](help://synoptic/sch-node-model)). It is saved in the file as the `kind` field, but SCHEMATIC is now the only value that field can have in a NEWLY saved file.

An earlier version of this editor also had a second screen kind, PLAN (an isometric plot plan, with its own canvas and its own library of tile-based objects) - it has been removed entirely. The `kind` field stays in the file format only so an OLDER file saved with `kind: "PLAN"` still opens: such a file loads normally, its screen is silently converted to SCHEMATIC, and a notice about that appears in the Messages panel - the file is NOT rejected, and the schema version number (`schema_version`) does not change.

A file with no `kind` field at all (every file saved before this concept existed) loads as SCHEMATIC with no message at all - that was, and still is, the only sensible default screen kind.
