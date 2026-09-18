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
import type { Device } from './DeviceSchema';

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

/**
 * feat/live-view: the controller's tag values ({tag: value}) while
 * Studio's "Na żywo" is on, null when it goes off - device-bound symbols
 * draw their live state (store/liveSlice.ts). Never touches the document.
 */
export function setLiveValuesFromStudio(values: Record<string, unknown> | null): void {
  useStore.getState().setLiveValues(values && typeof values === 'object' ? values : null);
}

/** Studio just wrote projekt.epw with this editor's document inside - nothing here is unsaved any more. */
export function markSavedByStudio(name: string): void {
  useStore.getState().setFileName(name || null);
  useStore.getState().setDirty(false);
}

/**
 * Punkt 2 / luka 7 ("unify the two apparatus registries"): Studio's own
 * "Aparaty" list, pushed in as DeviceSchema.ts Devices (project_panels.py's
 * device_to_synoptic_dict()). ADD-ONLY like cards and locations: a device
 * this editor already has under that id keeps its own richer fields
 * (name, designation, unit, ranges...) untouched. Returns the ids added.
 */
export function importDevicesFromStudio(devices: Device[]): string[] {
  const state = useStore.getState();
  const existing = new Set(state.devices.map((d) => d.id));
  const added: string[] = [];
  for (const device of devices) {
    if (!device || typeof device.id !== 'string' || !device.id || existing.has(device.id)) continue;
    state.addDevice(device);
    existing.add(device.id);
    added.push(device.id);
  }
  return added;
}
