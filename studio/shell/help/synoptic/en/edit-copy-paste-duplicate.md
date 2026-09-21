# 9.3 Copying, Pasting, Duplicating

Ctrl+C copies the current selection (objects, wires and meters together, whichever is non-empty) to the editor's own internal clipboard. Ctrl+V pastes it, offsetting the pasted elements by exactly one grid cell right and down from the original - so a paste never lands invisibly right on top of the original.

Ctrl+D duplicates the selection IN PLACE, with the same offset paste uses, without touching the clipboard - the clipboard keeps whatever was copied earlier.

Alt+drag is a third way: it leaves a SILENT copy exactly where the drag started (unselected, no history entry of its own), while the original element keeps being dragged under the cursor - the whole event (the copy plus the move) counts as one action in the history.
