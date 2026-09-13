// The Synoptic editor's interface translation layer.
//
// The same shape as the Studio shell's own (studio/shell/i18n.py): one
// dictionary per language in locales/<code>.json, dotted keys, English as
// the fallback, and it never throws - a missing key shows the key rather
// than an empty control.
//
// The language comes from the page address (?lang=pl - Studio passes its
// own current language when it opens the editor), then from what was last
// chosen in this browser, then English, the platform language.
//
// Symbol names are looked up by their registry type ("water.ball_valve")
// through symbolName(), not through tr(): a type contains a dot, and a
// dotted-key lookup would split it.

import en from './locales/en.json';
import pl from './locales/pl.json';

export type Language = 'en' | 'pl';

export const LANGUAGES: Language[] = ['en', 'pl'];

type Dictionary = { [key: string]: string | Dictionary };

const DICTIONARIES: Record<Language, Dictionary> = {
  en: en as Dictionary,
  pl: pl as Dictionary,
};

const STORAGE_KEY = 'epw-synoptic/language';

function isLanguage(value: unknown): value is Language {
  return value === 'en' || value === 'pl';
}

/** The language the editor should start in: the address, then the last choice in this browser, then English. */
export function detectLanguage(search?: string): Language {
  try {
    const query = new URLSearchParams(search ?? globalThis.location?.search ?? '').get('lang');
    if (isLanguage(query)) return query;
    const stored = globalThis.localStorage?.getItem(STORAGE_KEY);
    if (isLanguage(stored)) return stored;
  } catch {
    // No location / storage (a test, a locked-down browser): English.
  }
  return 'en';
}

let active: Language = detectLanguage();

export function getLanguage(): Language {
  return active;
}

export function setLanguage(language: Language): void {
  active = isLanguage(language) ? language : 'en';
  try {
    globalThis.localStorage?.setItem(STORAGE_KEY, active);
  } catch {
    // Remembering the choice is a convenience, not a requirement.
  }
}

function lookup(dictionary: Dictionary, key: string): string | undefined {
  let node: string | Dictionary | undefined = dictionary;
  for (const part of key.split('.')) {
    if (node && typeof node === 'object' && part in node) {
      node = node[part];
    } else {
      return undefined;
    }
  }
  return typeof node === 'string' ? node : undefined;
}

/** The interface text for `key` in `language` (the active one by default), with {name} placeholders filled from `params`. */
export function tr(key: string, params?: Record<string, string | number>, language: Language = active): string {
  const value = lookup(DICTIONARIES[language], key) ?? lookup(DICTIONARIES.en, key) ?? key;
  if (!params) return value;
  return value.replace(/\{(\w+)\}/g, (match, name: string) => (name in params ? String(params[name]) : match));
}

function symbolTable(language: Language): Record<string, string> {
  const table = DICTIONARIES[language].symbol;
  return table && typeof table === 'object' ? (table as Record<string, string>) : {};
}

/** A symbol's display name in `language`, falling back to English, then to `fallback` (the registry label), then to the type itself. */
export function symbolName(type: string, fallback?: string, language: Language = active): string {
  return symbolTable(language)[type] ?? symbolTable('en')[type] ?? fallback ?? type;
}

/** Every name a symbol is known by, in every language - what the library search matches against. */
export function symbolNamesInAllLanguages(type: string): string[] {
  return LANGUAGES.map(language => symbolTable(language)[type]).filter((name): name is string => !!name);
}
