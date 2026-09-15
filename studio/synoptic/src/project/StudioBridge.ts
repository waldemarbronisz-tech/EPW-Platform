// Task "Studio osadza ekrany i logikę w projekt.epw" (user report:
// "tworząc synoptykę w projekcie i zapisując projekt na głównym pasku,
// synoptyka nie zapisuje się [...] dalej to traktowane jest jako osobne
// programy"). Studio's own Save/Open (studio/shell/main_window.py) reads
// this editor's whole document out through projectDataForStudio() and
// hands it back through loadProjectFromStudio() - the screens live INSIDE
// projekt.epw (SPEC: "Ekrany są W ŚRODKU pliku projektu"), the .epwsyn
// file stays an exchange format. main.tsx puts these three on `window`
// for synoptic_panel.py; nothing else calls them.
//
// Pure store/ProjectManager calls, no DOM, so they are unit-testable.
import { ProjectManager } from './ProjectManager';
import { useStore } from '../store';

/** The EPW_SYNOPTIC document as JSON text, or null when the editor's own validation refuses to save (the same refusal Save As shows). */
export function projectDataForStudio(): string | null {
  return ProjectManager.getProjectData();
}

/**
 * Replaces the editor's content with `text` (an EPW_SYNOPTIC document
 * Studio read from projekt.epw) - or with a fresh empty project when
 * Studio has no screens for it yet. `name` is the Studio project's name,
 * shown where a file name used to be. Clean afterwards: it IS what the
 * project file holds.
 */
export function loadProjectFromStudio(text: string | null, name: string): boolean {
  if (!text) {
    ProjectManager.newProject(name || 'New Project');
    useStore.getState().setFileName(name || null);
    useStore.getState().setDirty(false);
    return true;
  }
  const ok = ProjectManager.loadProject(text, name || 'projekt.epw');
  if (ok) useStore.getState().setDirty(false);
  return ok;
}

/** Studio just wrote projekt.epw with this editor's document inside - nothing here is unsaved any more. */
export function markSavedByStudio(name: string): void {
  useStore.getState().setFileName(name || null);
  useStore.getState().setDirty(false);
}
