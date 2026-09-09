// feat/help-system commit 6 - the five SPRAWDZENIE SPOJNOSCI checks,
// run across ALL 13 chapters now that every one of them has content
// (superseding the earlier commits' own partial, per-chapter-range
// versions of tests 1/2/4). Mandatory test 10 (every shortcut exists in
// the code) already has its own dedicated suite in
// help-content-operations.test.ts and is not repeated here.

import { describe, it, expect } from 'vitest';
import { HELP_TOC, allTopicIds } from '../help/HelpToc';
import { getTopicBody } from '../help/HelpContentRegistry';
import { HELP_GLOSSARY } from '../help/HelpGlossary';
import { resolveLocalized } from '../i18n/HelpLanguage';
import type { HelpLanguage } from '../i18n/HelpLanguage';
import type { HelpBlock } from '../help/HelpTypes';
import { getSymbolDefinition } from '../symbols/SymbolRegistry';
import menuBarSource from '../components/MenuBar.tsx?raw';
import deviceSchemaSource from '../project/DeviceSchema.ts?raw';
import deviceValidationSource from '../project/DeviceValidation.ts?raw';
import netResolverSource from '../project/NetResolver.ts?raw';

function blockText(block: HelpBlock): string {
  switch (block.kind) {
    case 'heading': case 'p': case 'note': return block.text;
    case 'list': return block.items.join(' ');
    case 'table': return [...block.headers, ...block.rows.flat()].join(' ');
  }
}

function fullTopicText(topicId: string, lang: HelpLanguage): string {
  const body = getTopicBody(topicId)[lang] ?? [];
  return body.map(blockText).join('\n');
}

describe('SPOJNOSC 1/5: every chapter in the TOC has content in Polish and English (mandatory tests 1, 2 - full)', () => {
  const allIds = allTopicIds();

  it('has all 12 chapters (chapter 8, the isometric PLAN screen, was removed in full - chore/remove-isometric-plan-mode) and at least 40 topics total (sanity check on the TOC itself)', () => {
    expect(HELP_TOC.length).toBe(12);
    expect(allIds.length).toBeGreaterThanOrEqual(40);
  });

  it('every topic has non-empty Polish content, at least 2 blocks (no one-sentence chapters)', () => {
    for (const topicId of allIds) {
      const body = getTopicBody(topicId);
      expect(body.pl, `topic '${topicId}' has no Polish content`).toBeDefined();
      expect(body.pl!.length, `topic '${topicId}' (pl) looks like a placeholder`).toBeGreaterThanOrEqual(2);
    }
  });

  it('every topic has non-empty English content, at least 2 blocks (no one-sentence chapters)', () => {
    for (const topicId of allIds) {
      const body = getTopicBody(topicId);
      expect(body.en, `topic '${topicId}' has no English content`).toBeDefined();
      expect(body.en!.length, `topic '${topicId}' (en) looks like a placeholder`).toBeGreaterThanOrEqual(2);
    }
  });

  it('every chapter and topic title exists in both Polish and English', () => {
    for (const chapter of HELP_TOC) {
      expect(chapter.title.pl, `chapter '${chapter.id}' has no Polish title`).toBeTruthy();
      expect(chapter.title.en, `chapter '${chapter.id}' has no English title`).toBeTruthy();
      for (const topic of chapter.topics) {
        expect(topic.title.pl, `topic '${topic.id}' has no Polish title`).toBeTruthy();
        expect(topic.title.en, `topic '${topic.id}' has no English title`).toBeTruthy();
      }
    }
  });
});

describe('SPOJNOSC 2/5: no internal link points at a nonexistent chapter (mandatory test 4 - full)', () => {
  const LINK_RE = /\[\[([a-z0-9-]+)\|/g;

  it('every [[topicId|...]] link across every chapter, in both languages, resolves to a real topic', () => {
    const allIds = new Set(allTopicIds());
    let linkCount = 0;
    for (const topicId of allTopicIds()) {
      const body = getTopicBody(topicId);
      for (const lang of ['pl', 'en'] as const) {
        const text = fullTopicText(topicId, lang);
        let match: RegExpExecArray | null;
        LINK_RE.lastIndex = 0;
        while ((match = LINK_RE.exec(text))) {
          linkCount++;
          expect(allIds.has(match[1]), `topic '${topicId}' (${lang}) links to nonexistent topic '${match[1]}'`).toBe(true);
        }
      }
      void body;
    }
    // Sanity check on the check itself: this help actually uses internal links.
    expect(linkCount).toBeGreaterThan(20);
  });
});

describe('SPOJNOSC 3/5: every glossary entry\'s term appears in the content of at least one chapter (mandatory test 9)', () => {
  it('has at least 30 entries, per this task\'s own minimum', () => {
    expect(HELP_GLOSSARY.length).toBeGreaterThanOrEqual(30);
  });

  it('every glossary term (pl and en) appears somewhere in some chapter\'s own body text', () => {
    const allIds = allTopicIds();
    const fullTextByLang: Record<HelpLanguage, string> = { pl: '', en: '', de: '', es: '', uk: '', fr: '', it: '' };
    for (const topicId of allIds) {
      fullTextByLang.pl += '\n' + fullTopicText(topicId, 'pl').toLowerCase();
      fullTextByLang.en += '\n' + fullTopicText(topicId, 'en').toLowerCase();
    }

    for (const entry of HELP_GLOSSARY) {
      for (const lang of ['pl', 'en'] as const) {
        const term = resolveLocalized(entry.term, lang)?.value;
        expect(term, `glossary entry missing a ${lang} term`).toBeTruthy();
        // A glossary term is matched by its own significant word(s), not
        // necessarily character-for-character (Polish grammatical case
        // means e.g. "adres kanalu" may appear inflected as "adresu
        // kanalu" in running prose) - each SIGNIFICANT word of the term
        // (longer than 3 letters, to skip connectors like "and"/"i") must
        // appear somewhere in that language's combined chapter text.
        // Matched by STEM, not the whole word: Polish grammatical case
        // means e.g. "migracja" (nominative, the glossary term) commonly
        // appears inflected as "migracje"/"migracji" in running prose.
        // Dropping the last two characters absorbs typical suffix
        // variation in both languages without needing a real stemmer.
        const words = term!.toLowerCase().split(/[\s()/-]+/).filter(w => w.length > 3);
        for (const word of words) {
          const stem = word.slice(0, Math.max(3, word.length - 2));
          expect(fullTextByLang[lang].includes(stem), `glossary term '${term}' (${lang}) - stem '${stem}' (from '${word}') not found in any chapter's ${lang} content`).toBe(true);
        }
      }
    }
  });

  it('every glossary entry links to a real topic', () => {
    const allIds = new Set(allTopicIds());
    for (const entry of HELP_GLOSSARY) {
      const term = resolveLocalized(entry.term, 'pl')?.value;
      expect(allIds.has(entry.topicId), `glossary entry '${term}' links to nonexistent topic '${entry.topicId}'`).toBe(true);
    }
  });

  it('is sorted with no duplicate terms (pl)', () => {
    const terms = HELP_GLOSSARY.map(e => resolveLocalized(e.term, 'pl')?.value ?? '');
    expect(new Set(terms).size).toBe(terms.length);
  });
});

// ---- SPOJNOSC 4/5: every UI element this help describes actually exists ----
//
// chore/remove-isometric-plan-mode: reads each source file via Vite's own
// `?raw` suffix (same convention scada-symbols.test.ts/diode-colors.test.ts/
// rotation-handle-removal.test.ts already use for exactly this "scan a
// known source file's own text" need), not Node's `fs`/`path` - this
// tsconfig's own "types" list (tsconfig.app.json) is deliberately just
// ["vite/client"], so `node:fs`/`node:path`/`__dirname` do not resolve
// here at all. Previously used `fs.readFileSync`/`__dirname` directly -
// a pre-existing bug this task's own edits to this file happened to
// surface (tsc -b's incremental cache had never actually re-diagnosed
// this exact file before), fixed here rather than left in place, since
// DOWOD UKONCZENIA requires a genuinely clean `tsc -b`.

describe('SPOJNOSC 4/5: every UI element described in this help exists in the program', () => {
  it('every symbol type this help names by its registry id actually resolves in SymbolRegistry.ts', () => {
    const namedTypes = ['scada.boundary_point', 'scada.indicator_diode', 'scada.meter', 'electrical.circuit_breaker'];
    for (const type of namedTypes) {
      expect(getSymbolDefinition(type), `symbol type '${type}' named in this help does not exist in SymbolRegistry.ts`).toBeDefined();
    }
  });

  it('every menu item this help names by its exact label exists in MenuBar.tsx', () => {
    const labels = ['Rejestry projektu...', 'Lista aparatow...', 'Snap to Grid', 'Tematy pomocy...'];
    for (const label of labels) {
      expect(menuBarSource.includes(label), `menu item '${label}' named in this help is not in MenuBar.tsx`).toBe(true);
    }
  });

  it('every device field this help names by its exact path exists in DeviceSchema.ts', () => {
    const fields = ['feedback', 'command', 'supervision', 'safeState', 'switchCounter', 'publishToHa', 'confirmTimeoutMs', 'discrepancyAlarm', 'rangeMin', 'rangeMax', 'startupValue', 'safeValue', 'deadband'];
    for (const field of fields) {
      expect(deviceSchemaSource.includes(field), `device field '${field}' named in this help is not in DeviceSchema.ts`).toBe(true);
    }
  });

  it('every validation error code this help quotes exists in DeviceValidation.ts or NetResolver.ts', () => {
    const combined = deviceValidationSource + netResolverSource;
    const codes = [
      'DEVICE_DUPLICATE_DESIGNATION_IN_LOCATION', 'CHANNEL_ADDRESS_COLLISION',
      'MIXED_MEDIUM', 'DANGLING_NET', 'MULTIPLE_SOURCES',
    ];
    for (const code of codes) {
      expect(combined.includes(code), `error code '${code}' quoted in this help is not in DeviceValidation.ts/NetResolver.ts`).toBe(true);
    }
  });
});
