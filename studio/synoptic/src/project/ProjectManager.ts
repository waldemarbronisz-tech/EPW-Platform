import { validateProjectSchema, createEmptyProject, CURRENT_SCHEMA_VERSION, FORMAT_NAME } from './ProjectSchema';
import { runMigrations } from './Migrations';
import type { EPWProjectSchema } from './ProjectSchema';
import { useStore } from '../store';
import type { ScreenKind } from '../store';
import { GRID_SIZE } from '../theme/ScadaTheme';
import { HELP_DEFAULT_LANGUAGE } from '../i18n/HelpLanguage';

export class ProjectManager {
  // feat/isometric-engine commit 5: kind defaults to SCHEMATIC, same as
  // createEmptyProject itself - every existing one-argument call site
  // (MenuBar.tsx's plain "New") keeps creating a schematic project.
  static newProject(name: string = "New Project", kind: ScreenKind = 'SCHEMATIC') {
    const emptyProj = createEmptyProject(name, kind);
    this.loadProjectToStore(emptyProj, false);
    useStore.getState().addMessage(`[INFO] Project created: ${name}`);
  }

  static loadProject(data: string, fileName: string) {
    try {
      let parsed = JSON.parse(data);

      if (!parsed || typeof parsed !== 'object' || parsed.schema_version > CURRENT_SCHEMA_VERSION) {
         useStore.getState().addMessage(`[ERROR] Unsupported or invalid project schema format`);
         return false;
      }

      parsed = runMigrations(parsed);

      const validation = validateProjectSchema(parsed);
      if (!validation.valid) {
        const errorIssue = validation.issues.find(i => i.severity === 'ERROR');
        useStore.getState().addMessage(`[ERROR] Validation failed: ${errorIssue?.message}`);
        return false;
      }

      this.loadProjectToStore(parsed, false);
      useStore.getState().setFileName(fileName);
      useStore.getState().addMessage(`[INFO] Project loaded: ${fileName}`);
      return true;
    } catch (e: any) {
      useStore.getState().addMessage(`[ERROR] Failed to parse project file: ${e.message}`);
      return false;
    }
  }

  static getProjectData(): string | null {
    // The live arrays are the ACTIVE screen (project/ScreenContent.ts),
    // so they have to be parked into screenContents before anything
    // reads all of them - otherwise saving would write the active
    // screen twice and whatever it last replaced not at all.
    useStore.getState().captureActiveScreen();
    const state = useStore.getState();
    const proj: EPWProjectSchema = {
      format: FORMAT_NAME,
      schema_version: CURRENT_SCHEMA_VERSION,
      project: {
        name: state.projectName,
        description: state.projectMetadata.description,
        created_at: state.projectMetadata.created_at, // Preserved
        modified_at: new Date().toISOString() // Updated
      },
      canvas: state.canvasConfig,
      objects: state.objects,
      connections: state.connections || [],
      meters: state.meters || [],
      signalPanels: state.signalPanels || [],
      frames: state.frames || [],
      walls: state.walls || [],
      circuits: state.circuits || [],
      screens: state.screens,
      activeScreenId: state.activeScreenId,
      screenContents: state.screenContents,
      groupCommands: state.groupCommands || [],
      setpointPanels: state.setpointPanels || [],
      devices: state.devices || [],
      locations: state.locations || [],
      cards: state.cards || [],
      kind: state.screenKind,
      helpLanguage: state.helpLanguage
    };
    const validation = validateProjectSchema(proj);
    if (!validation.valid) {
       const errorIssue = validation.issues.find(i => i.severity === 'ERROR');
       useStore.getState().addMessage(`[ERROR] Save Aborted! Validation failed: ${errorIssue?.message}`);
       return null;
    }
    return JSON.stringify(proj, null, 2);
  }

  private static loadProjectToStore(project: EPWProjectSchema, isDirty: boolean) {
    // chore/remove-isometric-plan-mode 5e: `kind` is optional and additive
    // (ProjectSchema.ts) and SCHEMATIC is now the only value this editor
    // ever writes or recognizes - but a file saved by an earlier build
    // may still literally contain `kind: "PLAN"`. That file must still
    // LOAD (never rejected, no schema version bump), with its screen
    // silently treated as SCHEMATIC instead - "silently" only from
    // validateProjectSchema's point of view; a message is posted below,
    // once loadProject's own caller has a chance to see it, so the
    // conversion is not invisible to whoever opened the file. `project`
    // is read here as `any` deliberately: EPWProjectSchema's own `kind`
    // field is typed to the CURRENT, narrowed ScreenKind ('SCHEMATIC'
    // only) - a raw loaded file has no such guarantee at runtime.
    const rawKind = (project as any).kind;
    const isLegacyPlanKind = rawKind === 'PLAN';

    useStore.setState({
      objects: project.objects,
      connections: project.connections || [],
      meters: project.meters || [],
      signalPanels: project.signalPanels || [],
      frames: project.frames || [],
      walls: project.walls || [],
      circuits: project.circuits || [],
      // A file written before screens existed has none - it becomes a
      // one-screen project, which is exactly what it was.
      screens: project.screens?.length ? project.screens : [{ id: 'screen-1', name: 'Screen 1' }],
      activeScreenId: project.activeScreenId || project.screens?.[0]?.id || 'screen-1',
      screenContents: project.screenContents || {},
      // feat/workspace: views and undo stacks belong to the session that
      // made them, never to a project opened afterwards.
      screenViews: {},
      screenHistories: {},
      hiddenScreens: [],
      groupCommands: project.groupCommands || [],
      setpointPanels: project.setpointPanels || [],
      devices: project.devices || [],
      locations: project.locations || [],
      cards: project.cards || [],
      // A file with no `kind` field at all (every file saved before this
      // concept existed) loads as SCHEMATIC, same as a legacy PLAN one -
      // both simply fall back to the only value this field ever is now.
      screenKind: 'SCHEMATIC',
      helpLanguage: project.helpLanguage || HELP_DEFAULT_LANGUAGE,
      projectName: project.project.name,
      projectMetadata: {
        description: project.project.description || "",
        created_at: project.project.created_at || new Date().toISOString(),
        modified_at: project.project.modified_at || new Date().toISOString()
      },
      canvasConfig: {
        width: project.canvas.width || 1920,
        height: project.canvas.height || 1080,
        background: project.canvas.background || "#ffffff",
        // Bug fix (usterka 3): this hardcoded 20 was a leftover from
        // before GRID_SIZE existed - any loaded project file missing (or
        // explicitly saved with a falsy) canvas.gridSize silently
        // installed a grid pitch that disagreed with GRID_SIZE
        // everywhere else in the app, instead of GRID_SIZE actually
        // being that single source of truth.
        gridSize: project.canvas.gridSize || GRID_SIZE
      },
      isDirty: isDirty,
      selectedIds: [],
      history: [{
        objects: JSON.parse(JSON.stringify(project.objects)),
        connections: JSON.parse(JSON.stringify(project.connections || [])),
        meters: JSON.parse(JSON.stringify(project.meters || [])),
        signalPanels: JSON.parse(JSON.stringify(project.signalPanels || [])),
        frames: JSON.parse(JSON.stringify(project.frames || [])),
        walls: JSON.parse(JSON.stringify(project.walls || [])),
        circuits: JSON.parse(JSON.stringify(project.circuits || [])),
        groupCommands: JSON.parse(JSON.stringify(project.groupCommands || [])),
        setpointPanels: JSON.parse(JSON.stringify(project.setpointPanels || []))
      }],
      historyIndex: 0
    });

    // 5e: posted AFTER the state above lands, so it survives as a real
    // Messages-panel entry rather than being immediately overwritten by
    // whatever loadProject/newProject's own caller adds right after this
    // returns (both already add their own "[INFO] Project loaded/created"
    // message right after calling this).
    if (isLegacyPlanKind) {
      useStore.getState().addMessage('[INFO] This screen was saved as PLAN (the isometric plan mode), which no longer exists - converted to SCHEMATIC.');
    }
  }
}
