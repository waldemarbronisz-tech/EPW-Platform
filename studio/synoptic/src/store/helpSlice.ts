import type { StateCreator } from 'zustand';
import { HELP_DEFAULT_LANGUAGE } from '../i18n/HelpLanguage';
import type { HelpLanguage } from '../i18n/HelpLanguage';
import type { AppState } from './appState';

// feat/help-system commit 1 - the help language choice, persisted the
// same way this project already persists a setting that must survive a
// reload without touching localStorage/sessionStorage (GRANICE forbids
// both): screenKind is exactly this pattern already - plain Zustand
// state, written into the project file as an optional field
// (ProjectSchema.ts/ProjectManager.ts), read back on load, defaulting
// when the file (or the in-memory session, before any save) has none.
//
// This does mean the choice is REMEMBERED PER PROJECT FILE, not as a
// standalone global preference - the only mechanism in this codebase
// that outlives a reload at all is the project file itself; there is no
// separate app-settings file. Documented as a deliberate, examined
// choice in this task's own completion report, not an oversight.
export type HelpSlice = Pick<AppState, 'helpLanguage' | 'setHelpLanguage'>;

export const createHelpSlice: StateCreator<AppState, [], [], HelpSlice> = (set) => ({
  helpLanguage: HELP_DEFAULT_LANGUAGE,
  setHelpLanguage: (language: HelpLanguage) => set({ helpLanguage: language, isDirty: true }),
});
