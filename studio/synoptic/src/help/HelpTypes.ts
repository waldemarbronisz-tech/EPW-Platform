// feat/help-system commit 2 - shared shape for the whole help system.
// Content is DATA (plain TypeScript objects), never Markdown or HTML -
// GRANICE forbids a new dependency (markdown-it, react-markdown, ...),
// and a small closed set of block types is enough for real technical
// documentation (headings, paragraphs, lists, tables, callouts, code/
// address examples) without needing a parser at all.

import type { HelpLanguage } from '../i18n/HelpLanguage';

/**
 * One topic's content, in one language. Paragraph text supports two tiny
 * inline markers, both handled by a plain string split in
 * HelpInlineText.tsx - not a markup language:
 *   [[topicId|visible label]]  - an internal cross-reference, clickable
 *   \`literal text\`             - rendered in FONT_VALUE (an address,
 *                                  a field name, an id)
 */
export type HelpBlock =
  | { kind: 'heading'; text: string }
  | { kind: 'p'; text: string }
  | { kind: 'list'; items: string[]; ordered?: boolean }
  | { kind: 'table'; headers: string[]; rows: string[][] }
  | { kind: 'note'; text: string };

export type HelpTopicBody = HelpBlock[];

export interface HelpTopicMeta {
  id: string;
  title: Partial<Record<HelpLanguage, string>>;
}

export interface HelpChapterMeta {
  id: string;
  title: Partial<Record<HelpLanguage, string>>;
  topics: HelpTopicMeta[];
}

export interface HelpGlossaryEntry {
  term: Partial<Record<HelpLanguage, string>>;
  definition: Partial<Record<HelpLanguage, string>>;
  /** The topic where this concept is covered in depth - the glossary entry links there. */
  topicId: string;
}
