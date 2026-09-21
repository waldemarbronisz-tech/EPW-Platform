# 10.4 Whether EPW-OS Can Already Read This Format

NO, not fully - checked directly in EPW-OS's own code. It has a `SynopticRuntimeAdapter` (`epw_os/gui/widgets/synoptic_runtime.py`) that checks `format === "EPW_SYNOPTIC"` and loads the `objects` array - but that is explicitly labeled in its own code as a "simplified mock" skeleton.

That skeleton does NOT read `connections` at all (the whole node-based wiring model, [5.1](help://synoptic/sch-node-model)), does NOT read `devices`/`locations`/`cards` (the whole device registry, chapter 4), and its own click handling assumes `bindings.command` is plain "target.action" text - while in this editor `bindings.command` is an object `{tag, data_type, access}`, not text. Exercising that path today would end in an error, not in working behavior.

EPW-OS's own code comment (`epw_os/gui/main_window.py`) says it outright: its main page "will host switchable synoptic screens once the Synoptic Editor integration lands" - meaning it has not landed yet. The bridge from this editor's file to a live screen in EPW-OS does not exist yet.
