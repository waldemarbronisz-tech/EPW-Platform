# EPW OS Synoptic Runtime Contract

## Purpose
The `.epwsyn` file is a purely declarative engineering format. The Synoptic Editor natively builds and validates this schema against visual boundaries and connection topology logic (e.g. tracking Orthogonal routing points, preventing cross-domain links like Water to AC Power). The Synoptic Editor **does not** execute logic, nor does it poll Modbus or parse alarm queues.

## Schema Interpretation
The `.epwsyn` file consists of:
1. `project` (name, dates)
2. `canvas` (width, height, rendering metrics)
3. `objects` (nodes representing technical symbols)
4. `connections` (edges structurally mapping ports and `waypoints`)

## Runtime Binding
EPW OS logic services parse `.epwsyn` by translating the specific typed `bindings` property on each `SynopticObject`.

```json
"bindings": {
  "state": { "tag": "EG.KM1.STATE", "data_type": "BOOL" },
  "value": { "tag": "EPM01.UL1.RMS", "data_type": "REAL" },
  "command": { "tag": "EG.KM1.CMD", "data_type": "BOOL", "access": "WRITE" },
  "alarm": { "tag": "EG.KM1.ALM", "data_type": "BOOL" },
  "quality": { "tag": "EPM01.QUALITY", "data_type": "INT" }
}
```

The runtime translates these bindings into real-time TagManager queries.

## Rendering Previews vs Reality
The editor explicitly stores visualization states under `editor.preview_state`. This is intended exclusively for UI designers to preview colors and animations (e.g., verifying what a fault popup looks like). The EPW OS runtime **must ignore** `editor.preview_state` and explicitly rely on resolving the state dict payload returned via TagManager evaluation.
