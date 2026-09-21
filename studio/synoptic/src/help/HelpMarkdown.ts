// The Synoptic editor's help, rendered as Markdown for EPW Studio's one
// help (studio/shell/help/unified.py): Studio, the screen editor and the
// logic editor are one engineering program, so their help is one tree in
// one language, wherever you stand. The content stays DATA here
// (HelpTypes.ts); this module only turns it into text, and
// tools/help_export/export.mjs writes that text into
// studio/shell/help/synoptic/ (committed, like shared/symbols/geometry.json -
// the script is how you change it, help-export.test.ts is what notices
// when it is stale).
//
// Cross-references: `[[topicId|label]]` becomes `[label](help://synoptic/topicId)`,
// the namespaced key the unified help resolves; `\`literal\`` stays Markdown code.

import { HELP_TOC } from './HelpToc';
import { getTopicBody, placeholderBody } from './HelpContentRegistry';
import { HELP_GLOSSARY } from './HelpGlossary';
import type { HelpBlock } from './HelpTypes';
import type { HelpLanguage } from '../i18n/HelpLanguage';

export const HELP_LANGUAGES: HelpLanguage[] = ['pl', 'en'];

export interface RenderedHelp {
  toc: { chapters: { id: string; title: Record<string, string>; topics: { id: string; title: Record<string, string> }[] }[] };
  files: Record<string, Record<string, string>>;   // files[lang][topicId] = markdown
}

/** `[[id|label]]` -> a help://synoptic/ link; everything else verbatim. */
export function inlineToMarkdown(text: string): string {
  return text.replace(/\[\[([^\]|]+)\|([^\]]*)\]\]/g, (_m, id: string, label: string) => `[${label}](help://synoptic/${id.trim()})`);
}

function cell(text: string): string {
  return inlineToMarkdown(text).replace(/\|/g, '\\|');
}

export function blockToMarkdown(block: HelpBlock, lang: HelpLanguage): string {
  switch (block.kind) {
    case 'heading':
      return `## ${inlineToMarkdown(block.text)}`;
    case 'p':
      return inlineToMarkdown(block.text);
    case 'list':
      return block.items.map((item, i) => `${block.ordered ? `${i + 1}.` : '-'} ${inlineToMarkdown(item)}`).join('\n');
    case 'table': {
      const head = `| ${block.headers.map(cell).join(' | ')} |`;
      const rule = `| ${block.headers.map(() => '---').join(' | ')} |`;
      const rows = block.rows.map(row => `| ${row.map(cell).join(' | ')} |`);
      return [head, rule, ...rows].join('\n');
    }
    case 'note':
      return `> **${lang === 'pl' ? 'Uwaga' : 'Note'}:** ${inlineToMarkdown(block.text)}`;
    default:
      return '';
  }
}

function glossaryMarkdown(lang: HelpLanguage): string {
  const entries = [...HELP_GLOSSARY].sort((a, b) => (a.term[lang] || '').localeCompare(b.term[lang] || '', lang));
  return entries.map(entry =>
    `**${entry.term[lang] || ''}** — ${inlineToMarkdown(entry.definition[lang] || '')} ` +
    `[→](help://synoptic/${entry.topicId})`
  ).join('\n\n');
}

export function topicMarkdown(topicId: string, title: string, lang: HelpLanguage): string {
  const body = topicId === 'glossary-all'
    ? glossaryMarkdown(lang)
    : (getTopicBody(topicId)[lang] ?? placeholderBody(topicId)).map(b => blockToMarkdown(b, lang)).join('\n\n');
  return `# ${title}\n\n${body}\n`;
}

export function renderHelpMarkdown(): RenderedHelp {
  const files: Record<string, Record<string, string>> = {};
  for (const lang of HELP_LANGUAGES) files[lang] = {};
  const chapters = HELP_TOC.map(chapter => ({
    id: chapter.id,
    title: { pl: chapter.title.pl || chapter.title.en || chapter.id, en: chapter.title.en || chapter.title.pl || chapter.id },
    topics: chapter.topics.map(topic => {
      const title: Record<string, string> = {
        pl: topic.title.pl || topic.title.en || topic.id, en: topic.title.en || topic.title.pl || topic.id,
      };
      for (const lang of HELP_LANGUAGES) files[lang][topic.id] = topicMarkdown(topic.id, title[lang], lang);
      return { id: topic.id, title };
    }),
  }));
  return { toc: { chapters }, files };
}
