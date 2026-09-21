# A Symbol Shows a Red Outline

SYMPTOM: a schematic symbol has a dashed red outline, even though it otherwise renders normally.

CAUSE: that symbol's Aparat field points at an id no longer present in the device registry - usually because that device was deleted from the Device List after the symbol had already been pointing at it. A matching warning should be in the Messages panel.

FIX: select the symbol, pick the correct device from the Aparat dropdown in Properties (or (brak) if the symbol should become pure graphics), or recreate a device under the same id if the deletion was a mistake.
