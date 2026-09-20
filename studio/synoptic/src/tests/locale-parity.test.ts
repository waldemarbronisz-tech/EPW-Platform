// The two catalogues say the same things.
//
// Standing instruction: "jeżeli polski to wszędzie ma być polski".
// Adding a string in one language and forgetting the other does not
// fail anything at build time - tr() falls back, so the panel simply
// shows one English line in a Polish session and nobody notices until a
// user does. That is precisely the rot this guards.
//
// It compares the SHAPE of the two files, not their words: every key in
// one exists in the other, at the same depth, and no Polish entry is
// still the English sentence copied across unchanged.

import { describe, it, expect } from 'vitest';
import en from '../i18n/locales/en.json';
import pl from '../i18n/locales/pl.json';

type Dictionary = { [key: string]: string | Dictionary };

/** Every leaf key, dotted - "lighting.flux" rather than a nested shape. */
function leaves(table: Dictionary, prefix = ''): string[] {
  return Object.entries(table).flatMap(([key, value]) => {
    const path = prefix ? `${prefix}.${key}` : key;
    return typeof value === 'string' ? [path] : leaves(value as Dictionary, path);
  });
}

function leaf(table: Dictionary, path: string): string | undefined {
  const value = path.split('.').reduce<string | Dictionary | undefined>(
    (node, part) => (node && typeof node === 'object' ? (node as Dictionary)[part] : undefined),
    table
  );
  return typeof value === 'string' ? value : undefined;
}

const english = leaves(en as Dictionary);
const polish = leaves(pl as Dictionary);

describe('the interface catalogues', () => {
  it('sanity: both are real catalogues, not an empty import', () => {
    expect(english.length).toBeGreaterThan(100);
    expect(leaf(en as Dictionary, 'lighting.flux')).toBeTruthy();
  });

  it('has no English key without a Polish one', () => {
    expect(english.filter(key => !polish.includes(key))).toEqual([]);
  });

  it('has no Polish key without an English one', () => {
    // The other direction matters too: a stale Polish key is a string
    // nothing can ever show, and it hides a rename that half-landed.
    expect(polish.filter(key => !english.includes(key))).toEqual([]);
  });

  it('keeps every {placeholder} on both sides', () => {
    // tr() fills {name} from params. A placeholder dropped in
    // translation shows a literal gap; one invented shows "{lux}".
    const placeholders = (text: string) => (text.match(/\{(\w+)\}/g) || []).sort();
    const mismatched = english.filter(key => {
      const a = placeholders(leaf(en as Dictionary, key) || '');
      const b = placeholders(leaf(pl as Dictionary, key) || '');
      return a.join(',') !== b.join(',');
    });
    expect(mismatched).toEqual([]);
  });

  it('has no Polish entry that is still the English sentence', () => {
    // A short label legitimately matches - "Uo", "MQTT", "X". A whole
    // sentence identical in both files is a copy nobody came back to.
    const untranslated = english.filter(key => {
      const a = leaf(en as Dictionary, key) || '';
      const b = leaf(pl as Dictionary, key) || '';
      return a === b && a.trim().split(/\s+/).length >= 4;
    });
    expect(untranslated).toEqual([]);
  });
});
