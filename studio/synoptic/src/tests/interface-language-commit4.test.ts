// fix/tank-language-and-media commit 4 - the three mandatory tests for
// "unify interface language to English" (tests 17, 18, 19).
//
// Reads the whole source tree via Vite's own `import.meta.glob` (eager,
// `?raw`) rather than Node's `fs` - this tsconfig's own "types" list
// (tsconfig.app.json: ["vite/client"]) has no Node globals at all, the
// same constraint help-consistency.test.ts's and
// isometric-plan-mode-removed.test.ts's own header comments already
// document, and `import.meta.glob` is the Vite-native equivalent of a
// recursive directory read, already fully typed under vite/client with
// no new dependency needed.

import { describe, it, expect } from 'vitest';
import { HELP_TOC } from '../help/HelpToc';
import { HELP_GLOSSARY } from '../help/HelpGlossary';
import { resolveLocalized } from '../i18n/HelpLanguage';
import { getSymbolsByCategory } from '../symbols/SymbolRegistry';

// Every .ts/.tsx file under src/, this test file's own sibling files
// included - eager+raw so the whole set is available synchronously.
const allSourceFiles = import.meta.glob('../**/*.{ts,tsx}', { query: '?raw', import: 'default', eager: true }) as Record<string, string>;

// GRANICE excludes from this task's own translation: the help system's
// content (its 7-language layer, Polish content there is intentional),
// its i18n machinery, this test tree itself (test titles/comments are
// allowed to describe Polish source data, e.g. quoting an old label),
// and docs/ reference files (untouched by this task, out of scope for
// interface code review). Only genuine interface source is scanned.
const EXCLUDED_PATH_FRAGMENTS = ['/help/', '/i18n/', '/tests/'];

function isInterfaceFile(path: string): boolean {
  if (EXCLUDED_PATH_FRAGMENTS.some(f => path.includes(f))) return false;
  return path.endsWith('.ts') || path.endsWith('.tsx');
}

const DIACRITICS_RE = /[ĄąĆćĘęŁłŃńÓóŚśźŻżŹ]/;

// Strips both // line comments and the full body of every /* ... */
// block comment (including multi-line JSX {/* ... */} blocks, whose
// continuation lines carry no leading // or * of their own) before
// scanning - a naive per-line "starts with //" check misses exactly
// those continuation lines.
function nonCommentLines(source: string): string[] {
  const withoutBlockComments = source.replace(/\/\*[\s\S]*?\*\//g, '');
  return withoutBlockComments.split('\n').filter(line => !line.trim().startsWith('//'));
}

describe('test 17: no Polish diacritic survives in interface source, outside help/i18n/tests', () => {
  it('sanity: the glob actually sees real interface files (a passing empty-glob would prove nothing)', () => {
    const interfaceFiles = Object.keys(allSourceFiles).filter(isInterfaceFile);
    expect(interfaceFiles.length).toBeGreaterThan(100);
  });

  it('sanity: this exclusion genuinely drops the help/i18n trees, not everything', () => {
    // Vite's own import.meta.glob never surfaces this test file's
    // sibling tests in the first place (test files are outside its
    // normal module graph), so /tests/ is excluded structurally
    // regardless of EXCLUDED_PATH_FRAGMENTS - only help/i18n need
    // asserting here.
    const excluded = Object.keys(allSourceFiles).filter(p => !isInterfaceFile(p));
    expect(excluded.some(p => p.includes('/help/'))).toBe(true);
    expect(excluded.some(p => p.includes('/i18n/'))).toBe(true);
    expect(Object.keys(allSourceFiles).some(p => p.includes('/tests/'))).toBe(false);
  });

  it('no interface source file has a Polish diacritical character outside a comment', () => {
    const offenders: { path: string; line: string }[] = [];
    for (const [path, source] of Object.entries(allSourceFiles)) {
      if (!isInterfaceFile(path)) continue;
      for (const line of nonCommentLines(source)) {
        if (DIACRITICS_RE.test(line)) {
          offenders.push({ path, line: line.trim().slice(0, 120) });
        }
      }
    }
    expect(offenders, JSON.stringify(offenders, null, 2)).toEqual([]);
  });
});

describe('test 18: library group (category) names are in English', () => {
  it('every visible category name in the Object Library is an English word/acronym, not a Polish one', () => {
    const categories = Object.keys(getSymbolsByCategory());
    expect(categories.length).toBeGreaterThan(0);
    // The old Polish category 'TEREN' (fix/tank-language-and-media
    // commit 4) must be gone, replaced by 'SITE'.
    expect(categories).not.toContain('TEREN');
    expect(categories).toContain('SITE');
    // No category name contains a Polish diacritic either.
    for (const cat of categories) {
      expect(DIACRITICS_RE.test(cat), `category '${cat}' contains a Polish diacritic`).toBe(false);
    }
  });
});

describe('test 19: help content is unchanged (still Polish, untouched by this task)', () => {
  it('the help chapter/topic titles this task started from are still present verbatim in Polish', () => {
    // A handful of known anchors from HelpToc.ts, spot-checked rather
    // than hashing the whole file - if any of these ever legitimately
    // needs to change, it will be a deliberate edit to help content,
    // not a silent casualty of this task's own interface translation.
    const ch1 = HELP_TOC.find(c => c.id === 'ch1');
    expect(ch1?.title.pl).toBe('1. Wprowadzenie');
    const introWhat = ch1?.topics.find(t => t.id === 'intro-what');
    expect(introWhat?.title.pl).toBe('1.1 Czym jest EPW-Synoptic-Editor');
  });

  it('the help system keeps at least 30 Polish glossary terms with real Polish text', () => {
    const plTerms = HELP_GLOSSARY.map(e => resolveLocalized(e.term, 'pl')?.value ?? '');
    expect(plTerms.length).toBeGreaterThanOrEqual(30);
    // Sanity: at least some of them are still recognizably Polish
    // words (this codebase's own convention writes Polish without
    // diacritics throughout, so a diacritic check would prove
    // nothing here) - this help content was never in scope for this
    // task's own translation pass, so it must still read as Polish.
    const polishStems = ['zachowanie', 'zacisk', 'wezel', 'oznaczenie', 'sprzezenie'];
    expect(plTerms.some(t => polishStems.some(s => t.toLowerCase().includes(s)))).toBe(true);
  });

  it('a known glossary definition (Polish) this task started from is still present verbatim', () => {
    // A second, independent anchor (SPOJNOSC 3/5's own glossary check
    // covers structure/counts; this pins actual wording) - fix/
    // tank-language-and-media's own GRANICE excludes help content (and
    // its language machinery) from the interface translation this task
    // performs, so this exact Polish sentence must still read as it did
    // before commit 4, unlike every other Polish sentence this task
    // deliberately rewrote elsewhere in the interface.
    const busbar = HELP_GLOSSARY.find(e => resolveLocalized(e.term, 'en')?.value === 'Busbar');
    const plDefinition = busbar ? resolveLocalized(busbar.definition, 'pl')?.value : undefined;
    expect(plDefinition).toBe('Przewod w stylu BUS, wizualnie grubszy, przeznaczony do podlaczania wielu odbiorow na calej dlugosci.');
  });
});
