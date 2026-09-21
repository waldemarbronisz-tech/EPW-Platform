// Writes the Synoptic editor's help as Markdown into
// studio/shell/help/synoptic/ (toc.json + <lang>/<topic>.md) for EPW
// Studio's one help - see src/help/HelpMarkdown.ts. Run after any change
// to src/help/*:  node tools/help_export/export.mjs
// src/tests/help-export.test.ts fails while the committed files are stale.
import { register } from 'node:module';
import { pathToFileURL, fileURLToPath } from 'node:url';
import path from 'node:path';
import fs from 'node:fs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(HERE, '..', '..', '..', '..');
const OUT_DIR = path.join(REPO_ROOT, 'studio', 'shell', 'help', 'synoptic');

// Node 24 strips types itself; the geometry exporter's own hook resolves
// the editor's extension-less relative imports.
register(pathToFileURL(path.join(HERE, '..', 'geometry_export', 'resolve_ts_ext.mjs')).href, import.meta.url);

const { renderHelpMarkdown, HELP_LANGUAGES } = await import(pathToFileURL(path.join(HERE, '..', '..', 'src', 'help', 'HelpMarkdown.ts')).href);

const rendered = renderHelpMarkdown();
fs.mkdirSync(OUT_DIR, { recursive: true });
fs.writeFileSync(path.join(OUT_DIR, 'toc.json'), JSON.stringify(rendered.toc, null, 2) + '\n', 'utf-8');
let written = 0;
for (const lang of HELP_LANGUAGES) {
  const dir = path.join(OUT_DIR, lang);
  fs.mkdirSync(dir, { recursive: true });
  const wanted = new Set(Object.keys(rendered.files[lang]).map(id => `${id}.md`));
  for (const stale of fs.readdirSync(dir).filter(name => name.endsWith('.md') && !wanted.has(name))) {
    fs.unlinkSync(path.join(dir, stale));
  }
  for (const [id, markdown] of Object.entries(rendered.files[lang])) {
    fs.writeFileSync(path.join(dir, `${id}.md`), markdown, 'utf-8');
    written += 1;
  }
}
console.log(`help export: ${rendered.toc.chapters.length} chapters, ${written} files -> ${OUT_DIR}`);
