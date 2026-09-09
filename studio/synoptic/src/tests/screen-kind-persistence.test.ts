// chore/remove-isometric-plan-mode: the screen kind still round-trips
// through ProjectManager exactly like it always did (terrain-
// persistence.test.ts's own convention, before that file was removed
// along with the isometric PLAN mode it exercised) - SCHEMATIC is now
// the only value it is ever written with. Separately, mandatory test
// 12: a file saved by an EARLIER build with `kind: "PLAN"` must still
// LOAD - never rejected, no schema version bump - with its screen
// silently converted to SCHEMATIC and a message posted about it, per
// this task's own explicit 5e requirement.

import { describe, it, expect, beforeEach } from 'vitest';
import { useStore } from '../store';
import { ProjectManager } from '../project/ProjectManager';
import { createEmptyProject } from '../project/ProjectSchema';

function resetStore() {
  useStore.setState({
    objects: [], connections: [], meters: [], signalPanels: [], frames: [], devices: [],
    screenKind: 'SCHEMATIC', messages: [],
    selectedIds: [], selectedConnectionIds: [], selectedMeterIds: [], selectedSignalPanelIds: [], selectedFrameIds: [],
    history: [{ objects: [], connections: [], meters: [], signalPanels: [], frames: [] }],
    historyIndex: 0
  });
}

describe('createEmptyProject - kind defaults', () => {
  it('defaults to SCHEMATIC when no kind argument is given', () => {
    expect(createEmptyProject('Test').kind).toBe('SCHEMATIC');
  });
});

describe('Screen kind round-trip through ProjectManager', () => {
  beforeEach(resetStore);

  it('ProjectManager.newProject defaults to SCHEMATIC', () => {
    ProjectManager.newProject('Test');
    expect(useStore.getState().screenKind).toBe('SCHEMATIC');
  });

  it('getProjectData includes the store screenKind (always SCHEMATIC)', () => {
    const json = ProjectManager.getProjectData();
    const parsed = JSON.parse(json!);
    expect(parsed.kind).toBe('SCHEMATIC');
  });

  it('loading a project file with no kind field at all loads as SCHEMATIC - the task\'s own explicit default', () => {
    const projectJson = ProjectManager.getProjectData();
    const project = JSON.parse(projectJson!);
    delete project.kind;

    const ok = ProjectManager.loadProject(JSON.stringify(project), 'legacy.epwsyn');

    expect(ok).toBe(true);
    expect(useStore.getState().screenKind).toBe('SCHEMATIC');
  });

  // Mandatory test 12.
  it('a file saved with kind "PLAN" (an earlier build, before the isometric PLAN mode was removed) still LOADS, converted to SCHEMATIC, with a message posted about it - never rejected', () => {
    const projectJson = ProjectManager.getProjectData();
    const project = JSON.parse(projectJson!);
    project.kind = 'PLAN';

    const ok = ProjectManager.loadProject(JSON.stringify(project), 'old-plan.epwsyn');

    expect(ok).toBe(true);
    expect(useStore.getState().screenKind).toBe('SCHEMATIC');
    const messages = useStore.getState().messages;
    expect(messages.some(m => /PLAN/.test(m.text) && /SCHEMATIC/.test(m.text))).toBe(true);
  });

  it('does NOT bump the schema version to load a legacy PLAN-kind file', () => {
    const projectJson = ProjectManager.getProjectData();
    const project = JSON.parse(projectJson!);
    project.kind = 'PLAN';
    const savedVersion = project.schema_version;

    ProjectManager.loadProject(JSON.stringify(project), 'old-plan.epwsyn');

    // The loaded file's own schema_version is unchanged - this editor's
    // own CURRENT_SCHEMA_VERSION never moved to accommodate this at all.
    expect(project.schema_version).toBe(savedVersion);
  });

  it('a file with no kind field loads with NO conversion message (it was never PLAN, there is nothing to report)', () => {
    const projectJson = ProjectManager.getProjectData();
    const project = JSON.parse(projectJson!);
    delete project.kind;

    ProjectManager.loadProject(JSON.stringify(project), 'legacy.epwsyn');

    const messages = useStore.getState().messages;
    expect(messages.some(m => /PLAN/.test(m.text))).toBe(false);
  });
});
