// feat/help-system commit 3 - chapters 1-4 content, and a strengthened
// version of mandatory tests 1/2/4/5 scoped to what exists so far (the
// full, all-13-chapters version of these checks is commit 6's own
// consistency test suite).

import { describe, it, expect } from 'vitest';
import { HELP_TOC, allTopicIds } from '../help/HelpToc';
import { getTopicBody } from '../help/HelpContentRegistry';
import { searchHelp } from '../help/HelpSearch';

const CHAPTERS_1_TO_4_TOPIC_IDS = HELP_TOC
  .filter(c => ['ch1', 'ch2', 'ch3', 'ch4'].includes(c.id))
  .flatMap(c => c.topics.map(t => t.id));

describe('Chapters 1-4 content (partial mandatory tests 1, 2)', () => {
  it('test 1 (partial): every chapter 1-4 topic has Polish content', () => {
    for (const topicId of CHAPTERS_1_TO_4_TOPIC_IDS) {
      const body = getTopicBody(topicId);
      expect(body.pl, `topic '${topicId}' has no Polish content`).toBeDefined();
      expect(body.pl!.length).toBeGreaterThan(0);
    }
  });

  it('test 2 (partial): every chapter 1-4 topic has English content', () => {
    for (const topicId of CHAPTERS_1_TO_4_TOPIC_IDS) {
      const body = getTopicBody(topicId);
      expect(body.en, `topic '${topicId}' has no English content`).toBeDefined();
      expect(body.en!.length).toBeGreaterThan(0);
    }
  });

  it('no chapter 1-4 topic is a single-sentence placeholder (at least 2 content blocks)', () => {
    for (const topicId of CHAPTERS_1_TO_4_TOPIC_IDS) {
      const body = getTopicBody(topicId);
      expect(body.pl!.length, `topic '${topicId}' (pl) looks like a placeholder`).toBeGreaterThanOrEqual(2);
      expect(body.en!.length, `topic '${topicId}' (en) looks like a placeholder`).toBeGreaterThanOrEqual(2);
    }
  });
});

describe('Internal links from chapters 1-4 (partial mandatory test 4)', () => {
  const LINK_RE = /\[\[([a-z0-9-]+)\|/g;

  it('every [[topicId|...]] link used anywhere in chapters 1-4 points at a real topic', () => {
    const allIds = new Set(allTopicIds());
    for (const topicId of CHAPTERS_1_TO_4_TOPIC_IDS) {
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

describe('searchHelp over real body text (mandatory test 5)', () => {
  it('test 5: a phrase that only appears in a topic\'s body (not its title) is found', () => {
    // 'przedrostek' (prefix) appears in reg-locations' body but not its title ('3.1 Lokalizacje').
    const results = searchHelp('przedrostek', 'pl');
    expect(results.some(r => r.topicId === 'reg-locations')).toBe(true);
    const hit = results.find(r => r.topicId === 'reg-locations')!;
    expect(hit.snippet.length).toBeGreaterThan(0);
  });

  it('the same body-text search works in English too', () => {
    const results = searchHelp('prefix', 'en');
    expect(results.some(r => r.topicId === 'reg-locations')).toBe(true);
  });

  it('a device-behavior term from chapter 4 is found by search', () => {
    const results = searchHelp('discrepancy', 'en');
    expect(results.some(r => r.topicId === 'dev-switched')).toBe(true);
  });
});
