// EPW Studio's one help reads this editor's help as Markdown from
// studio/shell/help/synoptic/ (HelpMarkdown.ts, written by
// tools/help_export/export.mjs). These tests pin the rendering and fail
// while the committed export is older than the content - the same
// contract shared/symbols/geometry.json has with the symbol library.

/// <reference types='node' />
import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import { blockToMarkdown, inlineToMarkdown, renderHelpMarkdown, HELP_LANGUAGES } from '../help/HelpMarkdown';
import { HELP_TOC } from '../help/HelpToc';

const OUT_DIR = path.resolve(__dirname, '..', '..', '..', 'shell', 'help', 'synoptic');

describe('help rendered as Markdown for Studio', () => {
  it('turns the inline markers and every block kind into Markdown', () => {
    expect(inlineToMarkdown('see [[dev-switched|4.4]] and `ELA1.DI.1`')).toBe('see [4.4](help://synoptic/dev-switched) and `ELA1.DI.1`');
    expect(blockToMarkdown({ kind: 'heading', text: 'H' }, 'pl')).toBe('## H');
    expect(blockToMarkdown({ kind: 'list', items: ['a', 'b'], ordered: true }, 'pl')).toBe('1. a\n2. b');
    expect(blockToMarkdown({ kind: 'table', headers: ['A', 'B|C'], rows: [['1', '2']] }, 'en'))
      .toBe('| A | B\\|C |\n| --- | --- |\n| 1 | 2 |');
    expect(blockToMarkdown({ kind: 'note', text: 'n' }, 'pl')).toBe('> **Uwaga:** n');
    expect(blockToMarkdown({ kind: 'note', text: 'n' }, 'en')).toBe('> **Note:** n');
  });

  it('renders every topic of the table of contents in both languages, titled, with resolvable links', () => {
    const rendered = renderHelpMarkdown();
    const ids = new Set(HELP_TOC.flatMap(ch => ch.topics.map(t => t.id)));
    for (const lang of HELP_LANGUAGES) {
      expect(Object.keys(rendered.files[lang]).sort()).toEqual([...ids].sort());
      for (const [id, markdown] of Object.entries(rendered.files[lang])) {
        expect(markdown.startsWith('# ')).toBe(true);
        for (const m of markdown.matchAll(/help:\/\/synoptic\/([a-z0-9-]+)/g)) {
          expect(ids.has(m[1]), `${id} links to unknown ${m[1]}`).toBe(true);
        }
      }
    }
    expect(rendered.files.pl['glossary-all']).toContain('**Aparat**');
    expect(rendered.files.en['intro-what']).toContain('EPW-Synoptic-Editor');
  });

  it('the committed export in studio/shell/help/synoptic is current (run: node tools/help_export/export.mjs)', () => {
    const rendered = renderHelpMarkdown();
    const toc = JSON.parse(fs.readFileSync(path.join(OUT_DIR, 'toc.json'), 'utf-8'));
    expect(toc).toEqual(rendered.toc);
    for (const lang of HELP_LANGUAGES) {
      const dir = path.join(OUT_DIR, lang);
      const onDisk = fs.readdirSync(dir).filter((n: string) => n.endsWith('.md')).sort();
      expect(onDisk).toEqual(Object.keys(rendered.files[lang]).map(id => `${id}.md`).sort());
      for (const [id, markdown] of Object.entries(rendered.files[lang])) {
        expect(fs.readFileSync(path.join(dir, `${id}.md`), 'utf-8'), `${lang}/${id}.md is stale`).toBe(markdown);
      }
    }
  });
});
