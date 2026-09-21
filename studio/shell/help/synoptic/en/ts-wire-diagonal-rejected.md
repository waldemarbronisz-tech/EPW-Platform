# A Wire Will Not Go Diagonally

SYMPTOM: while drawing a wire, a diagonal mouse movement never produces a diagonal segment, only two right-angle ones.

CAUSE: this is not a defect - every wire segment MUST be horizontal or vertical (`appendWirePoint` in `WireDrawing.ts`); a diagonal movement is automatically split into a horizontal segment then a vertical one, forming one corner.

FIX: this is intended behavior - if a different corner shape is needed, click intermediate points to control exactly where the wire turns.
