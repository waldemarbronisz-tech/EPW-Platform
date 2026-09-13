// The editor's own keyboard commands that are not tied to the canvas
// gesture in progress: undo, redo and the work-mode switch.
//
// Undo and redo had no key at all - Ctrl+Z on the canvas did nothing, and
// the only way back was the menu. A text field keeps its own Ctrl+Z
// (the caller skips this while typing), so undoing a typo in Properties
// still undoes the typo.

import { modeFromShortcut } from '../project/WorkModes';
import type { WorkMode } from '../project/WorkModes';

export type EditorShortcut =
  | { kind: 'undo' }
  | { kind: 'redo' }
  | { kind: 'mode'; mode: WorkMode };

export function editorShortcut(event: { key: string; ctrlKey: boolean; metaKey?: boolean; altKey?: boolean; shiftKey?: boolean }): EditorShortcut | null {
  if (!(event.ctrlKey || event.metaKey) || event.altKey) return null;
  const key = event.key.toLowerCase();
  if (key === 'z') return event.shiftKey ? { kind: 'redo' } : { kind: 'undo' };
  if (key === 'y' && !event.shiftKey) return { kind: 'redo' };
  const mode = modeFromShortcut(event);
  return mode ? { kind: 'mode', mode } : null;
}
