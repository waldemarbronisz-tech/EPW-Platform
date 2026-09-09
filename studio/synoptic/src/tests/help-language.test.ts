// feat/help-system commit 1 - the help language layer, and mandatory
// test 3 (de/es/uk/fr/it are declared and resolve to the English
// fallback, never a blank page).

import { describe, it, expect, beforeEach } from 'vitest';
import { useStore } from '../store';
import {
  HELP_LANGUAGES, HELP_LANGUAGE_CODES, HELP_DEFAULT_LANGUAGE, HELP_FALLBACK_LANGUAGE,
  isHelpLanguage, resolveLocalized
} from '../i18n/HelpLanguage';
import { ProjectManager } from '../project/ProjectManager';

describe('HELP_LANGUAGES', () => {
  it('declares exactly the same seven languages as EPW-OS, in code form', () => {
    expect(HELP_LANGUAGE_CODES.sort()).toEqual(['de', 'en', 'es', 'fr', 'it', 'pl', 'uk'].sort());
  });

  it('pl and en are marked as having full content; the other five are declared but not yet translated', () => {
    const byCode = Object.fromEntries(HELP_LANGUAGES.map(l => [l.code, l.hasContent]));
    expect(byCode.pl).toBe(true);
    expect(byCode.en).toBe(true);
    expect(byCode.de).toBe(false);
    expect(byCode.es).toBe(false);
    expect(byCode.uk).toBe(false);
    expect(byCode.fr).toBe(false);
    expect(byCode.it).toBe(false);
  });

  it('the default help language is Polish, independent of any interface language', () => {
    expect(HELP_DEFAULT_LANGUAGE).toBe('pl');
  });

  it('isHelpLanguage rejects anything not in the declared list', () => {
    expect(isHelpLanguage('pl')).toBe(true);
    expect(isHelpLanguage('xx')).toBe(false);
    expect(isHelpLanguage(undefined)).toBe(false);
    expect(isHelpLanguage(42)).toBe(false);
  });
});

describe('resolveLocalized (mandatory test 3)', () => {
  it('returns the requested language directly when present, marked as not a fallback', () => {
    const content = { pl: 'Polski tekst', en: 'English text' };
    const result = resolveLocalized(content, 'pl');
    expect(result).toEqual({ value: 'Polski tekst', language: 'pl', isFallback: false });
  });

  it('test 3: de, es, uk, fr and it all resolve to the English content, never undefined/empty', () => {
    const content = { en: 'English text' };
    for (const lang of ['de', 'es', 'uk', 'fr', 'it'] as const) {
      const result = resolveLocalized(content, lang);
      expect(result).not.toBeNull();
      expect(result!.value).toBe('English text');
      expect(result!.language).toBe(HELP_FALLBACK_LANGUAGE);
      expect(result!.isFallback).toBe(true);
    }
  });

  it('returns null (never a silent blank) only when neither the requested language nor English has anything', () => {
    const content = { pl: 'Polski tekst' };
    expect(resolveLocalized(content, 'de')).toBeNull();
  });

  it('requesting English itself when English is the only content is not a fallback', () => {
    const content = { en: 'English text' };
    const result = resolveLocalized(content, 'en');
    expect(result).toEqual({ value: 'English text', language: 'en', isFallback: false });
  });
});

describe('Help language persistence (store + project file)', () => {
  beforeEach(() => {
    useStore.setState({ helpLanguage: HELP_DEFAULT_LANGUAGE, isDirty: false });
  });

  it('defaults to Polish in a fresh store', () => {
    expect(useStore.getState().helpLanguage).toBe('pl');
  });

  it('setHelpLanguage updates the store and marks the project dirty', () => {
    useStore.getState().setHelpLanguage('de');
    expect(useStore.getState().helpLanguage).toBe('de');
    expect(useStore.getState().isDirty).toBe(true);
  });

  it('round-trips through ProjectManager save/load, same mechanism as devices/locations/cards', () => {
    useStore.getState().setHelpLanguage('fr');
    const json = ProjectManager.getProjectData();
    expect(json).not.toBeNull();

    useStore.setState({ helpLanguage: HELP_DEFAULT_LANGUAGE });
    const ok = ProjectManager.loadProject(json!, 'help-lang.epwsyn');

    expect(ok).toBe(true);
    expect(useStore.getState().helpLanguage).toBe('fr');
  });

  it('a project file with no saved helpLanguage field at all loads as the default (legacy file), not an error', () => {
    const projectJson = ProjectManager.getProjectData();
    const project = JSON.parse(projectJson!);
    delete project.helpLanguage;

    const ok = ProjectManager.loadProject(JSON.stringify(project), 'legacy.epwsyn');

    expect(ok).toBe(true);
    expect(useStore.getState().helpLanguage).toBe(HELP_DEFAULT_LANGUAGE);
  });
});
