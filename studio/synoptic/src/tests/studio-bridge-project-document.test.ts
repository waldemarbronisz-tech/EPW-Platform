// Task "Studio osadza ekrany i logike w projekt.epw" - the whole
// document in and out for Studio's own Save/Open (project/StudioBridge.ts,
// put on `window` by main.tsx). User report: "tworzac synoptyke w
// projekcie i zapisujac projekt na glownym pasku, synoptyka nie zapisuje
// sie".
import { describe, it, expect, beforeEach } from 'vitest';
import { useStore } from '../store';
import { ProjectManager } from '../project/ProjectManager';
import { loadProjectFromStudio, markSavedByStudio, projectDataForStudio } from '../project/StudioBridge';

describe('Studio project-document bridge', () => {
  beforeEach(() => {
    ProjectManager.newProject('Fresh');
  });

  it('hands the current document out as the same EPW_SYNOPTIC JSON Save As would write', () => {
    useStore.getState().addObject({ type: 'water.ball_valve', x: 32, y: 32 } as never);
    const text = projectDataForStudio();
    expect(text).not.toBeNull();
    const doc = JSON.parse(text!);
    expect(doc.format).toBe('EPW_SYNOPTIC');
    expect(doc.project.name).toBe('Fresh');
    expect(JSON.stringify(doc)).toContain('water.ball_valve');
  });

  it('loads a document back, replacing the current one, and is clean afterwards', () => {
    useStore.getState().addObject({ type: 'water.ball_valve', x: 32, y: 32 } as never);
    const saved = projectDataForStudio()!;

    ProjectManager.newProject('Other');
    expect(useStore.getState().objects).toHaveLength(0);

    expect(loadProjectFromStudio(saved, 'Kotlownia')).toBe(true);
    expect(useStore.getState().objects.map(o => o.type)).toEqual(['water.ball_valve']);
    expect(useStore.getState().isDirty).toBe(false);
    expect(useStore.getState().fileName).toBe('Kotlownia');
  });

  it('an empty section means a fresh project, not an error', () => {
    useStore.getState().addObject({ type: 'water.ball_valve', x: 32, y: 32 } as never);
    expect(loadProjectFromStudio(null, 'Nowy projekt')).toBe(true);
    expect(useStore.getState().objects).toHaveLength(0);
    expect(useStore.getState().projectName).toBe('Nowy projekt');
    expect(useStore.getState().isDirty).toBe(false);
  });

  it('refuses a document that is not a synoptic project and keeps what was open', () => {
    useStore.getState().addObject({ type: 'water.ball_valve', x: 32, y: 32 } as never);
    expect(loadProjectFromStudio('{"format":"SOMETHING_ELSE"}', 'x')).toBe(false);
    expect(useStore.getState().objects).toHaveLength(1);
  });

  it('markSavedByStudio clears the dirty flag - Studio wrote the file', () => {
    useStore.getState().addObject({ type: 'water.ball_valve', x: 32, y: 32 } as never);
    expect(useStore.getState().isDirty).toBe(true);
    markSavedByStudio('projekt');
    expect(useStore.getState().isDirty).toBe(false);
    expect(useStore.getState().fileName).toBe('projekt');
  });
});
