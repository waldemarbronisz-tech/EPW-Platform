// feat/help-system commit 1 - the help system's own language layer.
//
// This is NOT interface translation. Every button label, panel title and
// message in this editor stays exactly as it is (Polish task text is
// explicit about this: "TO ZADANIE NIE TLUMACZY INTERFEJSU"). This file
// only names which languages the HELP CONTENT (src/help/) may exist in.
//
// Same seven languages as EPW-OS's own i18n layer (epw_os/i18n/__init__.py):
// Polish and English with full content, the other five declared and
// wired end to end but with no translated text yet - a topic in one of
// those five falls back to English (see HelpContentRegistry.ts), never
// to an empty page.

export type HelpLanguage = 'pl' | 'en' | 'de' | 'es' | 'uk' | 'fr' | 'it';

export interface HelpLanguageInfo {
  code: HelpLanguage;
  nativeName: string;
  /** False for the five declared-but-not-yet-translated languages - the language picker still lists them (task: "przygotowane"), it just means every topic in them will show the English-with-notice fallback. */
  hasContent: boolean;
}

// Order matches EPW-OS's own Settings dropdown (epw_os/i18n/__init__.py's
// LANGUAGES dict) - English first there because it is EPW-OS's own
// interface-translation default; this editor's help defaults to Polish
// instead (see HELP_DEFAULT_LANGUAGE below), a deliberate difference
// this task's own spec states outright, not an inconsistency.
export const HELP_LANGUAGES: HelpLanguageInfo[] = [
  { code: 'en', nativeName: 'English', hasContent: true },
  { code: 'pl', nativeName: 'Polski', hasContent: true },
  { code: 'de', nativeName: 'Deutsch', hasContent: false },
  { code: 'es', nativeName: 'Español', hasContent: false },
  { code: 'uk', nativeName: 'Українська', hasContent: false },
  { code: 'fr', nativeName: 'Français', hasContent: false },
  { code: 'it', nativeName: 'Italiano', hasContent: false },
];

export const HELP_LANGUAGE_CODES: HelpLanguage[] = HELP_LANGUAGES.map(l => l.code);

export function isHelpLanguage(value: unknown): value is HelpLanguage {
  return typeof value === 'string' && (HELP_LANGUAGE_CODES as string[]).includes(value);
}

/** Task's own explicit default - independent of EPW-OS's interface-translation default (English), which is a different setting for a different purpose. */
export const HELP_DEFAULT_LANGUAGE: HelpLanguage = 'pl';

/** Every topic's ultimate fallback when the active language has no content - English, per EPW-OS's own convention (epw_os/core/help_content.py's FALLBACK_LANGUAGE) and this task's own spec ("gdy rozdzial nie ma tresci w wybranym jezyku, pokaz tresc angielska"). */
export const HELP_FALLBACK_LANGUAGE: HelpLanguage = 'en';

export interface LocalizedResolution<T> {
  value: T;
  /** The language the value actually came from - equals the requested language unless isFallback is true. */
  language: HelpLanguage;
  /** True when the requested language had nothing and this fell back to HELP_FALLBACK_LANGUAGE - the caller (HelpTopicView) uses this to show the "translation not yet available" notice the task requires, never a blank page. */
  isFallback: boolean;
}

/**
 * Content-shape-agnostic language resolution: works the same whether
 * `content` holds a topic's title (a string) or its full body (a block
 * array) - both commit 2's TOC and commits 3-5's actual chapter content
 * are `Partial<Record<HelpLanguage, T>>` maps for exactly this reason.
 * Returns null only when NEITHER the requested language NOR English has
 * an entry at all - a genuine authoring gap, not a normal untranslated-
 * language case - so the caller can still show something honest rather
 * than a silent blank.
 */
export function resolveLocalized<T>(content: Partial<Record<HelpLanguage, T>>, requested: HelpLanguage): LocalizedResolution<T> | null {
  const direct = content[requested];
  if (direct !== undefined) {
    return { value: direct, language: requested, isFallback: false };
  }
  if (requested !== HELP_FALLBACK_LANGUAGE) {
    const fallback = content[HELP_FALLBACK_LANGUAGE];
    if (fallback !== undefined) {
      return { value: fallback, language: HELP_FALLBACK_LANGUAGE, isFallback: true };
    }
  }
  return null;
}
