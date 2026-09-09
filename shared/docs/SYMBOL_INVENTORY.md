# Symbol Inventory

Generated 2026-09-09T20:34:13.889Z by `generate_symbol_inventory.mjs`, which **executes** `studio/synoptic/src/symbols/SymbolRegistry.ts` (via Node + a small extensionless-import resolver hook, no build step) rather than parsing it as text - three registry files set `hiddenFromLibrary` on a whole category via a runtime `.forEach()`, not a field on each object literal, which only real execution catches.

Re-run: `node --experimental-strip-types shared/docs/generate_symbol_inventory.mjs`

## Totals

- **85 symbol definitions** in the registry.
- Hidden from the Object Library (still fully defined/placeable, just not offered as a new drag-in): **34** / 85.
- Have node-based-wiring `terminals`: **48**. Legacy `connectionPoints` only (no terminals): **19**. Neither: **18**.
- `isLine` (drawn as a line, not a boxed symbol): **2**. `isSurface` (background layer, e.g. grass/road): **2**. `supportsDynamicPorts` (bus-style, variable port count): **2**.
- Multi-state (`allowedStates.length > 1` - can visually change at runtime): **76**. Single-state (nothing to switch): **9**.
- Full set of state strings occurring anywhere in the registry (**37** distinct): `A`, `ACTIVE`, `B`, `BLINK`, `BLOWN`, `CENTER`, `CLOSED`, `CLOSING`, `DEAD`, `DEENERGIZED`, `ENERGIZED`, `FAULT`, `HEATING`, `HIGH`, `LEFT`, `LIVE`, `LOW`, `NISKI`, `NORMAL`, `OFF`, `ON`, `OPEN`, `OPENING`, `OTWARTA`, `QUALITY`, `RIGHT`, `RUN`, `RUNNING`, `SREDNI`, `STOP`, `TRIPPED`, `WYLACZONY`, `WYSOKI`, `W_RUCHU`, `ZALACZONY`, `ZAMKNIETA`, `ZAMKNIETY`.

### By category

| Category | Symbols |
|---|---|
| Electrical | 25 |
| Water | 23 |
| SCADA | 10 |
| Automation | 7 |
| Instrumentation | 6 |
| TEREN | 5 |
| Measurements | 4 |
| Graphics | 3 |
| HVAC | 2 |

## Real usage: the four example files vs. the library

| File | Objects | Distinct types |
|---|---|---|
| GOSPODARKA_WODNA.epwsyn | 15 | 12 |
| ENTRY_GATE_LIBRARY_TEST.epwsyn | 25 | 22 |
| LIBRARY_TEST.epwsyn | 13 | 13 |
| STATEFUL_SYMBOLS.epwsyn | 12 | 11 |

**47 distinct symbol types** are referenced across all four files combined (65 objects total) - against 85 defined in the library today. That is the number that sizes the rendering work, not 101 (the file count under `src/symbols/`) and not 85 (every symbol ever defined, most of them never drawn in these four projects).

⚠️ **3 of those referenced types do not exist in today's registry at all**: `electrical.cable`, `sensors.temperature`, `water.pipe`. These are stale `type` strings left over from an earlier version of the editor/library (a rename or removal since these example files were saved) - in the editor itself, `getSymbolDefinition()` returns `undefined` for them today (confirmed empirically, not assumed), which `ProjectSchema.ts`'s own validator already flags as `UNKNOWN_SYMBOL` (a WARNING, not a refusal - see `epwsyn_loader.py`'s own treatment of unresolved `deviceId`, same spirit). Any renderer needs an explicit "I don't know this symbol" fallback for exactly this reason, not just for symbols added after the renderer was built.

Full per-symbol data (every field, plus which of the four files uses it, if any): see `SYMBOL_INVENTORY.json`.
