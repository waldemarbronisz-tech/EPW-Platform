# EPW Synoptic Editor - Architecture Hardening Report

## LABEL ENGINE
**IMPLEMENTED**
- Centralized `ObjectLabelRenderer.tsx` respects independent `showDesignation` and `showName` properties.
- Labels are detached from bounding box hardcoding, supporting TOP, BOTTOM, LEFT, and RIGHT, and fully parsing Shift+Drag `labelOffsetX/Y` user overrides.
- Word wrapping and multiline displays cleanly map alongside symbol bounding properties.

## PORT ENGINE & MODEL
**IMPLEMENTED**
- Replaced ambiguous `ConnectionPoint` properties with strict definitions mapping `domain` (`electrical`, `water`, `hvac`, `data`, `control`), `medium`, and `direction` (`in`, `out`, `passive`).
- Completely audited the `SymbolRegistry`. Water components correctly parse as `water`, and automation RS485/ETH ports strictly register as `data`. Excess `bidirectional` fallbacks were stripped in favor of accurate `passive`/`in`/`out` definitions.
- Ports logically scale and maintain geometric rotation transforms inside the rendering loop.

## CONNECTION DRAG & ROUTING
**IMPLEMENTED**
- Drag-to-connect natively traces an ephemeral cursor wire until released onto an actively resolved port.
- Connection compatibility is enforced via `ConnectionService.ts` during the mouse-up sequence. The engine outright rejects connections spanning incompatible `domains` (e.g., `water` -> `electrical_ac`), duplicate connections, or invalid `IN` -> `IN` / `OUT` -> `OUT` directions.
- Single-use port constraints explicitly restrict standard logic endpoints from multiple taps.
- The default router utilizes strict orthogonal logic identifying the fastest standard `L` and `S-bends` derived directly from port node geometry.

## BUSBAR BEHAVIOR
**IMPLEMENTED**
- Converted `BusbarSymbol` from a heavy rect block into a 4px precise engineering trace housed in a scaled interactive bounding box.
- Dynamic attachment natively synthesizes connection endpoints relative to scale (`dyn_XX` percentages), avoiding the hardcoded P1-P5 limits entirely. Infinite parallel node drops are successfully preserved.

## ARCHITECTURE & SCHEMA PERSISTENCE
**IMPLEMENTED**
- Migrated out of unstructured object maps into strict `.epwsyn` format parsing via `ProjectSchema.ts` and `ProjectManager.ts`.
- Validation natively rejects invalid versions, missing fields, duplicate object/connection IDs, unresolved symbol types, and dangling connection parameters before committing to editor state.
- Project creation metrics (`created_at`) are structurally sealed against save-loop overwrites, exclusively mutating `modified_at`.
- Canvas configurations (`width`, `height`, `background`, `gridSize`) gracefully hydrate to standard state formats.
- `HistorySnapshot` ensures complete isolation across the Undo/Redo tracking timeline. Removed completely all `as any` type bypasses for strict structural assurance.

## RUNTIME BINDING CONTRACT
**IMPLEMENTED**
- Ripped out legacy data-bindings (`runtimeVariable`, `alarm`, `animation`).
- Converted the internal state mapping into strict typed `bindings` dictionaries targeting `state`, `value`, `command`, `alarm`, and `quality` tracking fields specifically requesting tag identifiers, formats, and `access` constraints.
- Generated `RUNTIME_CONTRACT.md` detailing exact deployment models mapping this topology.

## TEST SUITE & CI
**IMPLEMENTED**
- Configured `.github/workflows/ci.yml` triggering headless CI runs across Node v24.
- `vitest` unit-testing scripts established tracking Object generation bounds, geometric offsets, orthogonal logic calculations, port `domain` boundaries, and `.epwsyn` format parsing (duplicate tracking, validation checks). Current test suite executes 23 native unit checks against core infrastructure points.

All requested acceptance checks successfully verified through manual application usage and automated build tests.
