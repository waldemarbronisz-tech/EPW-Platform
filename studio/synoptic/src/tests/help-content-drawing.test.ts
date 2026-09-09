// feat/help-system commit 4 - chapters 5-7 content, extending the same
// partial checks help-content-core.test.ts already runs for chapters
// 1-4 (the full, all-thirteen-chapters version is commit 6's own
// consistency suite).

import { describe, it, expect } from 'vitest';
import { HELP_TOC, allTopicIds } from '../help/HelpToc';
import { getTopicBody } from '../help/HelpContentRegistry';
import { searchHelp } from '../help/HelpSearch';

const CHAPTERS_5_TO_7_TOPIC_IDS = HELP_TOC
  .filter(c => ['ch5', 'ch6', 'ch7'].includes(c.id))
  .flatMap(c => c.topics.map(t => t.id));

describe('Chapters 5-7 content (partial mandatory tests 1, 2)', () => {
  it('test 1 (partial): every chapter 5-7 topic has Polish content, at least 2 blocks', () => {
    for (const topicId of CHAPTERS_5_TO_7_TOPIC_IDS) {
      const body = getTopicBody(topicId);
      expect(body.pl, `topic '${topicId}' has no Polish content`).toBeDefined();
      expect(body.pl!.length).toBeGreaterThanOrEqual(2);
    }
  });

  it('test 2 (partial): every chapter 5-7 topic has English content, at least 2 blocks', () => {
    for (const topicId of CHAPTERS_5_TO_7_TOPIC_IDS) {
      const body = getTopicBody(topicId);
      expect(body.en, `topic '${topicId}' has no English content`).toBeDefined();
      expect(body.en!.length).toBeGreaterThanOrEqual(2);
    }
  });
});

describe('Internal links from chapters 5-7 (partial mandatory test 4)', () => {
  const LINK_RE = /\[\[([a-z0-9-]+)\|/g;

  it('every [[topicId|...]] link used anywhere in chapters 5-7 points at a real topic', () => {
    const allIds = new Set(allTopicIds());
    for (const topicId of CHAPTERS_5_TO_7_TOPIC_IDS) {
      const body = getTopicBody(topicId);
      for (const lang of ['pl', 'en'] as const) {
        for (const block of body[lang] ?? []) {
          const text = block.kind === 'table' ? [...block.headers, ...block.rows.flat()].join(' ')
            : block.kind === 'list' ? block.items.join(' ')
            : block.text;
          let match: RegExpExecArray | null;
          LINK_RE.lastIndex = 0;
          while ((match = LINK_RE.exec(text))) {
            expect(allIds.has(match[1]), `topic '${topicId}' (${lang}) links to nonexistent topic '${match[1]}'`).toBe(true);
          }
        }
      }
    }
  });
});

describe('searchHelp over chapters 5-7 body text', () => {
  it('finds the busbar topic by a body-only phrase', () => {
    const results = searchHelp('rozdzielacz', 'pl');
    expect(results.some(r => r.topicId === 'sch-wire-style')).toBe(true);
  });

  it('finds the meter/signal-panel "two meters" clarification by an English body phrase', () => {
    const results = searchHelp('two different "meters"', 'en');
    expect(results.some(r => r.topicId === 'elem-meter')).toBe(true);
  });
});
