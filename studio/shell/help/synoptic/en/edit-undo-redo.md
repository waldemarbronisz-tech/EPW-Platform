# 9.4 Undo and Redo - What Counts as One Action

Undo history covers objects, wires, meters, signal panels and frames TOGETHER as ONE combined snapshot per history-save call - not a separate history per element type. The limit is 100 entries.

ONE action in the history is: one drag (from mouse-down to mouse-up), one arrow-key press, one menu operation (Copy/Paste/Delete), one finished wire drawing. An attempt to save history where nothing actually changed (e.g. clicking into a field and leaving without editing it) is skipped, so it does not clutter the history with empty entries.

The project registries (locations, cards, devices) and the chosen help language are NOT part of this undo history - they are project settings, not drawing content; their changes cannot be undone through the Edit menu's undo.
