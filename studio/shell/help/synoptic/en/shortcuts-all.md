# 12. Keyboard Shortcuts

The list below is pulled directly from the keyboard handling in the code (`Canvas.tsx`, `App.tsx`, `HelpWindow.tsx`) - not from memory. If a shortcut seems obvious and is not listed here (e.g. Ctrl+Z/Ctrl+Y for undo/redo), that means this editor version only offers it from the Edit menu, not the keyboard - checked directly in the code, not assumed.

## Selection

| Shortcut | Action | Where |
| --- | --- | --- |
| Ctrl/Cmd+A | Select everything on the current screen | Schematic |
| Shift+click | Add/remove from the selection | Schematic |
| Escape | Clear selection (if nothing else is in progress) | Schematic |

## Editing

| Shortcut | Action | Where |
| --- | --- | --- |
| Ctrl/Cmd+C | Copy the selection | Schematic |
| Ctrl/Cmd+V | Paste (offset by one grid cell) | Schematic |
| Ctrl/Cmd+D | Duplicate the selection in place | Schematic |
| Delete / Backspace | Delete the selection | Schematic |
| Arrow keys | Move the selection by one grid cell (ten with Shift) | Schematic |

## View

| Shortcut | Action | Where |
| --- | --- | --- |
| Space (held) | Pan mode (hand cursor) | Schematic |
| Ctrl/Cmd+0 | Reset zoom to 100% | Schematic |
| Ctrl/Cmd+9 | Fit the view to all content | Schematic |

## Drawing tools

| Shortcut | Action | Where |
| --- | --- | --- |
| 1 / 2 / 3 | Pick a new wire's medium (electrical/water/ventilation) | Schematic |
| Enter | Finish drawing a wire | Schematic |
| Backspace (while drawing) | Undo the last wire point | Schematic |
| Alt+click on a wire | Insert a bend point | Schematic |
| Alt (held, while dragging) | Temporarily disable snap-to-grid | Schematic |

## Help

| Shortcut | Action |
| --- | --- |
| F1 | Open help on the topic related to the current selection |
| Escape | Close the help window |
