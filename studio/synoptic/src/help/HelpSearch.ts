// feat/help-system commit 2 - search over the currently active
// language's resolved content (title, falling back to English exactly
// like the body does - a topic showing English-with-a-notice is
// searched in English, not silently skipped).

import { HELP_TOC, allTopicIds, findTopicMeta } from './HelpToc';
import { getTopicBody, placeholderBody } from './HelpContentRegistry';
import { resolveLocalized } from '../i18n/HelpLanguage';
import type { HelpLanguage } from '../i18n/HelpLanguage';
import type { HelpBlock } from './HelpTypes';

function blockText(block: HelpBlock): string {
  switch (block.kind) {
    case 'heading': case 'p': case 'note': return block.text;
    case 'list': return block.items.join(' ');
    case 'table': return [...block.headers, ...block.rows.flat()].join(' ');
  }
}

export interface HelpSearchResult {
  topicId: string;
  title: string;
  /** A short window of body text around the first match, for display - '' when only the title matched. */
  snippet: string;
}

/**
 * Every topic whose resolved title OR body contains `query`
 * (case-insensitive). An empty/whitespace-only query matches nothing -
 * mandatory test: a blank search box should not just list every topic.
 * A query with no match anywhere returns an empty array without ever
 * throwing (mandatory test 6).
 */
export function searchHelp(query: string, language: HelpLanguage): HelpSearchResult[] {
  const needle = (query || '').trim().toLowerCase();
  if (!needle) return [];

  const results: HelpSearchResult[] = [];
  for (const topicId of allTopicIds()) {
    const meta = findTopicMeta(topicId);
    if (!meta) continue;
    const titleResolution = resolveLocalized(meta.title, language);
    const title = titleResolution?.value ?? topicId;

    const bodyResolution = resolveLocalized(getTopicBody(topicId), language);
    const body = bodyResolution?.value ?? placeholderBody(topicId);
    const fullText = body.map(blockText).join('\n');

    const titleHit = title.toLowerCase().includes(needle);
    const bodyIndex = fullText.toLowerCase().indexOf(needle);

    if (titleHit || bodyIndex >= 0) {
      let snippet = '';
      if (bodyIndex >= 0) {
        const start = Math.max(0, bodyIndex - 40);
        const end = Math.min(fullText.length, bodyIndex + needle.length + 40);
        snippet = `${start > 0 ? '…' : ''}${fullText.slice(start, end)}${end < fullText.length ? '…' : ''}`;
      }
      results.push({ topicId, title, snippet });
    }
  }
  return results;
}

/** Every chapter title, flattened - used only by tests that need to sanity-check the TOC itself is non-empty. */
export function allChapterIds(): string[] {
  return HELP_TOC.map(c => c.id);
}
