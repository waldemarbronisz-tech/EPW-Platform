#!/usr/bin/env node
// Generates SYMBOL_INVENTORY.json + SYMBOL_INVENTORY.md from the EPW
// Synoptic Editor's REAL symbol registry - by actually importing and
// running studio/synoptic/src/symbols/SymbolRegistry.ts, not by
// regex-parsing the .ts source as text.
//
// WHY EXECUTION, NOT TEXT PARSING: three of the nine registry files
// (automation.ts, graphics.ts, measurements.ts) set hiddenFromLibrary
// on every symbol in the category with a single trailing statement -
// `Object.values(xSymbols).forEach(def => { def.hiddenFromLibrary =
// true; })` - not a field on each object literal. A parser reading only
// object-literal syntax would report those 14 symbols as visible in the
// library, which is simply wrong. Running the real module is the only
// way this inventory can be trusted - see ts_extension_resolver.mjs for
// the one small loader hook this needs (Node's ESM loader, unlike
// Vite/tsc, does not resolve this project's extensionless relative
// imports on its own).
//
// Re-run any time the library changes:
//   node --experimental-strip-types shared/docs/generate_symbol_inventory.mjs
//
// No dependency added: node:module's register(), node:fs, node:path,
// node:url are all Node built-ins. --experimental-strip-types is a
// stock Node 22.6+ flag (this repo's studio/synoptic/src has no enums/
// namespaces/decorators - "erasable syntax" only - so plain type
// stripping is enough; no transform/build step needed).

import { register } from 'node:module';
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(HERE, '..', '..');
const SYNOPTIC_SRC = path.join(REPO_ROOT, 'studio', 'synoptic', 'src');
const EXAMPLES_DIR = path.join(REPO_ROOT, 'studio', 'synoptic', 'examples');

register(pathToFileURL(path.join(HERE, 'ts_extension_resolver.mjs')).href, import.meta.url);

const { SYMBOL_REGISTRY } = await import(
  pathToFileURL(path.join(SYNOPTIC_SRC, 'symbols', 'SymbolRegistry.ts')).href
);

const types = Object.keys(SYMBOL_REGISTRY).sort();

// --- Per-symbol facts (section 2.2) -------------------------------------

const symbols = types.map((type) => {
  const def = SYMBOL_REGISTRY[type];
  const terminalCount = Array.isArray(def.terminals) ? def.terminals.length : 0;
  const connectionPointCount = Array.isArray(def.connectionPoints) ? def.connectionPoints.length : 0;
  return {
    type,
    label: def.label,
    category: def.category,
    default_width: def.defaultWidth,
    default_height: def.defaultHeight,
    allowed_states: def.allowedStates ?? [],
    default_state: def.defaultState,
    terminal_count: terminalCount,
    connection_point_count: connectionPointCount,
    is_line: !!def.isLine,
    is_surface: !!def.isSurface,
    hidden_from_library: !!def.hiddenFromLibrary,
    supports_dynamic_ports: !!def.supportsDynamicPorts,
    designation_prefix: def.designationPrefix ?? null,
  };
});

// --- Aggregates ----------------------------------------------------------

const byCategory = {};
const allStatesSeen = new Set();
let hiddenCount = 0, terminalsCount = 0, connectionPointsOnlyCount = 0, neitherCount = 0;
let isLineCount = 0, isSurfaceCount = 0, dynamicPortsCount = 0;
let multiStateCount = 0, singleStateCount = 0;

for (const s of symbols) {
  byCategory[s.category] = (byCategory[s.category] || 0) + 1;
  s.allowed_states.forEach((st) => allStatesSeen.add(st));
  if (s.hidden_from_library) hiddenCount++;
  if (s.terminal_count > 0) terminalsCount++;
  else if (s.connection_point_count > 0) connectionPointsOnlyCount++;
  else neitherCount++;
  if (s.is_line) isLineCount++;
  if (s.is_surface) isSurfaceCount++;
  if (s.supports_dynamic_ports) dynamicPortsCount++;
  if (s.allowed_states.length > 1) multiStateCount++;
  else singleStateCount++;
}

// --- Real usage across the four real .epwsyn examples (section 2.3) -----

const exampleFiles = ['GOSPODARKA_WODNA.epwsyn', 'ENTRY_GATE_LIBRARY_TEST.epwsyn',
                       'LIBRARY_TEST.epwsyn', 'STATEFUL_SYMBOLS.epwsyn'];

const knownTypes = new Set(types);
const usedByType = new Map(); // type -> Set(filenames)
const perFile = {};

for (const filename of exampleFiles) {
  const filePath = path.join(EXAMPLES_DIR, filename);
  const doc = JSON.parse(readFileSync(filePath, 'utf-8'));
  const objects = doc.objects ?? [];
  const distinctHere = new Set();
  for (const obj of objects) {
    const t = obj.type;
    distinctHere.add(t);
    if (!usedByType.has(t)) usedByType.set(t, new Set());
    usedByType.get(t).add(filename);
  }
  perFile[filename] = { object_count: objects.length, distinct_types: distinctHere.size };
}

const usedTypes = [...usedByType.keys()].sort();
const usedTypesFoundInRegistry = usedTypes.filter((t) => knownTypes.has(t));
const usedTypesMissingFromRegistry = usedTypes.filter((t) => !knownTypes.has(t));

for (const s of symbols) {
  s.used_in_examples = usedByType.has(s.type) ? [...usedByType.get(s.type)].sort() : [];
}

const inventory = {
  generated_at: new Date().toISOString(),
  generated_by: 'shared/docs/generate_symbol_inventory.mjs (executes the real registry - see script header)',
  source: 'studio/synoptic/src/symbols/SymbolRegistry.ts',
  totals: {
    symbol_count: symbols.length,
    by_category: byCategory,
    hidden_from_library: hiddenCount,
    visible_in_library: symbols.length - hiddenCount,
    with_terminals: terminalsCount,
    with_connection_points_only: connectionPointsOnlyCount,
    with_neither_terminals_nor_connection_points: neitherCount,
    is_line: isLineCount,
    is_surface: isSurfaceCount,
    supports_dynamic_ports: dynamicPortsCount,
    multi_state_symbols: multiStateCount,
    single_state_symbols: singleStateCount,
    distinct_states_seen: [...allStatesSeen].sort(),
  },
  usage_in_examples: {
    examples_checked: exampleFiles,
    per_file: perFile,
    total_objects_across_examples: Object.values(perFile).reduce((a, f) => a + f.object_count, 0),
    distinct_types_referenced: usedTypes.length,
    distinct_types_found_in_current_registry: usedTypesFoundInRegistry.length,
    distinct_types_missing_from_current_registry: usedTypesMissingFromRegistry,
  },
  symbols,
};

writeFileSync(path.join(HERE, 'SYMBOL_INVENTORY.json'), JSON.stringify(inventory, null, 2) + '\n', 'utf-8');

// --- Markdown summary ------------------------------------------------------

function md() {
  const lines = [];
  lines.push('# Symbol Inventory');
  lines.push('');
  lines.push(`Generated ${inventory.generated_at} by \`generate_symbol_inventory.mjs\`, which ` +
             `**executes** \`studio/synoptic/src/symbols/SymbolRegistry.ts\` (via Node + a small ` +
             'extensionless-import resolver hook, no build step) rather than parsing it as text - ' +
             'three registry files set `hiddenFromLibrary` on a whole category via a runtime ' +
             '`.forEach()`, not a field on each object literal, which only real execution catches.');
  lines.push('');
  lines.push('Re-run: `node --experimental-strip-types shared/docs/generate_symbol_inventory.mjs`');
  lines.push('');
  lines.push('## Totals');
  lines.push('');
  lines.push(`- **${inventory.totals.symbol_count} symbol definitions** in the registry.`);
  lines.push(`- Hidden from the Object Library (still fully defined/placeable, just not offered as a new drag-in): **${inventory.totals.hidden_from_library}** / ${inventory.totals.symbol_count}.`);
  lines.push(`- Have node-based-wiring \`terminals\`: **${inventory.totals.with_terminals}**. Legacy \`connectionPoints\` only (no terminals): **${inventory.totals.with_connection_points_only}**. Neither: **${inventory.totals.with_neither_terminals_nor_connection_points}**.`);
  lines.push(`- \`isLine\` (drawn as a line, not a boxed symbol): **${inventory.totals.is_line}**. \`isSurface\` (background layer, e.g. grass/road): **${inventory.totals.is_surface}**. \`supportsDynamicPorts\` (bus-style, variable port count): **${inventory.totals.supports_dynamic_ports}**.`);
  lines.push(`- Multi-state (\`allowedStates.length > 1\` - can visually change at runtime): **${inventory.totals.multi_state_symbols}**. Single-state (nothing to switch): **${inventory.totals.single_state_symbols}**.`);
  lines.push(`- Full set of state strings occurring anywhere in the registry (**${inventory.totals.distinct_states_seen.length}** distinct): ${inventory.totals.distinct_states_seen.map((s) => `\`${s}\``).join(', ')}.`);
  lines.push('');
  lines.push('### By category');
  lines.push('');
  lines.push('| Category | Symbols |');
  lines.push('|---|---|');
  for (const [cat, count] of Object.entries(inventory.totals.by_category).sort((a, b) => b[1] - a[1])) {
    lines.push(`| ${cat} | ${count} |`);
  }
  lines.push('');
  lines.push('## Real usage: the four example files vs. the library');
  lines.push('');
  lines.push(`| File | Objects | Distinct types |`);
  lines.push('|---|---|---|');
  for (const [filename, stats] of Object.entries(inventory.usage_in_examples.per_file)) {
    lines.push(`| ${filename} | ${stats.object_count} | ${stats.distinct_types} |`);
  }
  lines.push('');
  lines.push(`**${inventory.usage_in_examples.distinct_types_referenced} distinct symbol types** are referenced across all four files combined ` +
             `(${inventory.usage_in_examples.total_objects_across_examples} objects total) - against ${inventory.totals.symbol_count} defined in the ` +
             `library today. That is the number that sizes the rendering work, not 101 (the file count under \`src/symbols/\`) and not ${inventory.totals.symbol_count} ` +
             '(every symbol ever defined, most of them never drawn in these four projects).');
  lines.push('');
  if (inventory.usage_in_examples.distinct_types_missing_from_current_registry.length > 0) {
    lines.push(`⚠️ **${inventory.usage_in_examples.distinct_types_missing_from_current_registry.length} of those referenced types do not exist in today's registry at all**: ` +
               inventory.usage_in_examples.distinct_types_missing_from_current_registry.map((t) => `\`${t}\``).join(', ') +
               '. These are stale `type` strings left over from an earlier version of the editor/library (a rename or removal since these example ' +
               'files were saved) - in the editor itself, `getSymbolDefinition()` returns `undefined` for them today (confirmed empirically, not assumed), ' +
               'which `ProjectSchema.ts`\'s own validator already flags as `UNKNOWN_SYMBOL` (a WARNING, not a refusal - see `epwsyn_loader.py`\'s own treatment of unresolved `deviceId`, same spirit). ' +
               'Any renderer needs an explicit "I don\'t know this symbol" fallback for exactly this reason, not just for symbols added after the renderer was built.');
    lines.push('');
  }
  lines.push('Full per-symbol data (every field, plus which of the four files uses it, if any): see `SYMBOL_INVENTORY.json`.');
  lines.push('');
  return lines.join('\n');
}

writeFileSync(path.join(HERE, 'SYMBOL_INVENTORY.md'), md(), 'utf-8');

console.log(`Wrote SYMBOL_INVENTORY.json + .md (${symbols.length} symbols, ` +
            `${inventory.usage_in_examples.distinct_types_referenced} used across the 4 real examples) to ${HERE}`);
