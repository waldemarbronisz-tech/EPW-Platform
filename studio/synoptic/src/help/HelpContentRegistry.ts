// feat/help-system commit 2 - merges every content-commit's own topic
// body map into one lookup. Empty for now (no content commit has run
// yet) - getTopicBody already handles that the same way it will handle
// a genuinely missing topic later: an honest placeholder, never a
// crash and never a silent blank (mirrors EPW-OS's own
// HelpContentStore.load_topic_markdown contract).
//
// Each content commit (3, 4, 5, 6) adds exactly one import and one
// entry to CONTENT_SOURCES below for its own module - a plain, explicit
// merge rather than an imperative registration call, so which content
// exists is visible by reading this one file, not by trusting that
// something else remembered to import it for its side effect.

import type { HelpBlock } from './HelpTypes';
import type { HelpLanguage } from '../i18n/HelpLanguage';
import { HELP_CONTENT_CORE } from './HelpContentCore';
import { HELP_CONTENT_DRAWING } from './HelpContentDrawing';
import { HELP_CONTENT_OPERATIONS } from './HelpContentOperations';
import { HELP_CONTENT_GLOSSARY } from './HelpContentGlossary';

export type HelpContentMap = Record<string, Partial<Record<HelpLanguage, HelpBlock[]>>>;

const CONTENT_SOURCES: HelpContentMap[] = [
  HELP_CONTENT_CORE,       // commit 3: chapters 1-4
  HELP_CONTENT_DRAWING,    // commit 4: chapters 5-7
  HELP_CONTENT_OPERATIONS, // commit 5: chapters 8-12
  HELP_CONTENT_GLOSSARY,   // commit 6: chapter 13
];

export function getTopicBody(topicId: string): Partial<Record<HelpLanguage, HelpBlock[]>> {
  for (const source of CONTENT_SOURCES) {
    if (source[topicId]) return source[topicId];
  }
  return {};
}

/** Never shown once every content commit has run - a temporary, honest stand-in for a topic id that exists in the TOC but has no body yet. */
export function placeholderBody(topicId: string): HelpBlock[] {
  return [
    { kind: 'p', text: `(Tresc rozdzialu '${topicId}' nie zostala jeszcze napisana.)` },
  ];
}
