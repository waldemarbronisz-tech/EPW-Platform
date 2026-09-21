# 2.3 Saving and Opening a Project

`File > Save` and `Save As...` write the whole project state to one `.epwsyn` file (JSON, `format: "EPW_SYNOPTIC"`) through the browser's own native file-save mechanism. `File > Open...` reads such a file back.

Everything is saved: project metadata, canvas configuration, objects and wires, meters and signal panels, frames, locations/cards/devices, the screen kind, and the chosen help language. Full file contents are covered in [10.1](help://synoptic/file-contents).

Loading a file with a schema version newer than what this build supports (`schema_version` field) is rejected with an error rather than a partial, unpredictable load - see [10.2](help://synoptic/file-versioning).
