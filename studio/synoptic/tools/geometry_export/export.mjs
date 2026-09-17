#!/usr/bin/env node
// Exports the WHOLE symbol library of the Synoptic Editor as plain
// drawing primitives - shared/symbols/geometry.json - for the EPW-OS
// runtime's own renderer (runtime/epw_os/gui/synoptic/). Grown from the
// reconnaissance spike in spike/geometry_export (see
// shared/docs/spike/GEOMETRY_EXPORT_SPIKE.md for why this is the chosen
// path): the real .tsx component of every symbol is executed as a plain
// function against stub react/react-konva/store modules, and the JSX
// tree it returns is walked into {primitive, props, children} records.
//
// What the file carries, per symbol type and per allowed state:
//   - the primitives in the symbol's OWN pixel space (reference_width x
//     reference_height, the registry's default size) - the runtime
//     scales them to the object's width/height/scaleX/scaleY exactly the
//     way the editor's own Group transform does;
//   - per-instance fields as MARKERS: a symbol that reads obj.fill,
//     obj.text, obj.designation, editor.preview_value... is exported
//     once with sentinel values and once with empty ones, and every prop
//     that differs becomes {"$template": "...{{field}}...", "$default":
//     <what the symbol draws when the field is empty>} - so the runtime
//     substitutes the real object's text/colour/value and still gets the
//     symbol's own fallback for an empty field;
//   - an animation directive for the symbols that animate (a table kept
//     here, read from their source - animation is not geometry);
//   - registry facts the renderer needs (default state, line/surface
//     flags, terminals, designation prefix).
//
// Run: `npm install && npm run export` in this directory (needs Node
// 22+ for the built-in TypeScript stripping the registry import relies
// on). Re-run whenever the symbol library changes; the runtime's tests
// compare the file against the registry.
import esbuild from 'esbuild';
import { register } from 'node:module';
import { pathToFileURL, fileURLToPath } from 'node:url';
import path from 'node:path';
import fs from 'node:fs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(HERE, '..', '..', '..', '..');
const SRC_DIR = path.resolve(HERE, '..', '..', 'src');
const SYMBOLS_DIR = path.join(SRC_DIR, 'symbols');
const BUILD_DIR = path.join(HERE, '.build');
const OUT_FILE = path.join(REPO_ROOT, 'shared', 'symbols', 'geometry.json');

register(pathToFileURL(path.join(HERE, 'resolve_ts_ext.mjs')).href, import.meta.url);

// --- what the browser would provide and the symbols may touch at import time
globalThis.window = globalThis.window || globalThis;
globalThis.localStorage = globalThis.localStorage || { getItem: () => null, setItem() {}, removeItem() {} };
globalThis.document = globalThis.document || {
  createElement: () => ({ getContext: () => null, style: {} }),
  addEventListener() {},
  removeEventListener() {},
};

// --- animation directives: not geometry, read from each symbol's source ---
// trigger_state: the state in which the symbol animates; the runtime's
// renderer applies the technique to the exported base pose.
const ANIMATION_DIRECTIVES = {
  'electrical.indicator_lamp': { type: 'blink', trigger_state: 'BLINK', half_period_ms: 500 },
  'hvac.fan': { type: 'rotate', trigger_state: 'RUNNING', rate_deg_per_sec: 900, target: 'rotating' },
};

const SENTINELS = {
  fill: '{{fill}}', border: '{{border}}', color: '{{color}}', text: '{{text}}', font: '{{font}}',
  designation: '{{designation}}', name: '{{name}}', description: '{{description}}', tag: '{{tag}}',
  textColor: '{{textColor}}', value: '{{value}}', unit: '{{unit}}', circuit: '{{circuit}}',
};
const FONT_SIZE_SENTINEL = 7777.5;

function fakeObject(type, category, width, height, state, withSentinels) {
  const s = (key) => (withSentinels ? SENTINELS[key] : '');
  return {
    id: 'export', type, category, x: 0, y: 0, rotation: 0, scaleX: 1, scaleY: 1,
    visible: true, locked: false, layer: 1, width, height,
    tag: s('tag'), description: s('description'), color: s('color'), fill: s('fill'), border: s('border'),
    text: s('text'), font: s('font'), fontSize: withSentinels ? FONT_SIZE_SENTINEL : 0, tooltip: '',
    customProperties: {}, designation: s('designation'), name: s('name'), textColor: withSentinels ? SENTINELS.textColor : undefined,
    circuit: s('circuit'),
    editor: { preview_state: state, preview_value: withSentinels ? SENTINELS.value : '', unit: s('unit'), format: '' },
  };
}

// --- SymbolRenderer.tsx is the one place that says which component draws which type
function readDispatchTable() {
  const source = fs.readFileSync(path.join(SYMBOLS_DIR, 'SymbolRenderer.tsx'), 'utf-8');
  const imports = new Map();
  for (const m of source.matchAll(/import\s*\{([^}]*)\}\s*from\s*'(\.[^']*)'/g)) {
    for (const raw of m[1].split(',')) {
      const name = raw.trim().split(/\s+as\s+/).pop();
      if (name) imports.set(name, m[2]);
    }
  }
  const dispatch = new Map();
  for (const m of source.matchAll(/case\s*'([a-z_]+\.[a-z0-9_]+)'\s*:\s*return\s*<(\w+)/g)) {
    dispatch.set(m[1], { component: m[2], file: imports.get(m[2]) });
  }
  return dispatch;
}

async function bundleComponents(dispatch) {
  fs.mkdirSync(BUILD_DIR, { recursive: true });
  const byFile = new Map();
  for (const [_type, { component, file }] of dispatch) {
    if (!file) continue;
    if (!byFile.has(file)) byFile.set(file, new Set());
    byFile.get(file).add(component);
  }
  let entry = '';
  let n = 0;
  const alias = new Map();
  for (const [file, names] of byFile) {
    const spec = path.posix.join(...path.relative(BUILD_DIR, path.join(SYMBOLS_DIR, file)).split(path.sep));
    const parts = [];
    for (const name of names) {
      const local = `C${n++}`;
      alias.set(name, local);
      parts.push(`${name} as ${local}`);
    }
    entry += `import { ${parts.join(', ')} } from '${spec.startsWith('.') ? spec : './' + spec}';\n`;
  }
  entry += 'export const COMPONENTS = {\n';
  for (const [type, { component, file }] of dispatch) {
    if (file) entry += `  ${JSON.stringify(type)}: ${alias.get(component)},\n`;
  }
  entry += '};\n';
  const entryPath = path.join(BUILD_DIR, 'entry.mjs');
  fs.writeFileSync(entryPath, entry, 'utf-8');

  const stubs = {
    react: path.join(HERE, 'stubs', 'react.js'),
    'react-konva': path.join(HERE, 'stubs', 'react-konva.js'),
    store: path.join(HERE, 'stubs', 'store.js'),
  };
  const stubPlugin = {
    name: 'epw-stubs',
    setup(build) {
      build.onResolve({ filter: /^react$/ }, () => ({ path: stubs.react }));
      build.onResolve({ filter: /^react\/jsx-runtime$/ }, () => ({ path: stubs.react }));
      build.onResolve({ filter: /^react-konva$/ }, () => ({ path: stubs['react-konva'] }));
      build.onResolve({ filter: /(^|\/)store(\/index)?$/ }, (args) => (
        args.path.startsWith('.') ? { path: stubs.store } : undefined
      ));
    },
  };
  const shim = path.join(BUILD_DIR, 'react-shim.js');
  fs.writeFileSync(shim, "import React from 'react';\nexport { React };\n", 'utf-8');
  const result = await esbuild.build({
    entryPoints: [entryPath],
    bundle: true,
    write: false,
    format: 'esm',
    platform: 'neutral',
    mainFields: ['module', 'main'],
    jsx: 'transform',
    jsxFactory: 'React.createElement',
    jsxFragment: 'React.Fragment',
    inject: [shim],
    plugins: [stubPlugin],
    logLevel: 'silent',
    loader: { '.json': 'json' },
  });
  const outPath = path.join(BUILD_DIR, 'components.mjs');
  fs.writeFileSync(outPath, result.outputFiles[0].text, 'utf-8');
  const mod = await import(pathToFileURL(outPath).href + '?t=' + Date.now());
  return mod.COMPONENTS;
}

// --- tree -> primitives ---------------------------------------------------------------
const PRIMITIVES = new Set(['Group', 'Rect', 'Circle', 'Ellipse', 'Line', 'Path', 'Text', 'Arc', 'Wedge',
  'RegularPolygon', 'Ring', 'Star']);
const DROPPED_PROPS = new Set(['key', 'ref', 'listening', 'draggable', 'name', 'id', 'perfectDrawEnabled',
  'shadowForStrokeEnabled', 'hitStrokeWidth', 'strokeHitEnabled', 'transformsEnabled']);

// Runs a clipFunc against a context that only records: rect(), arc(),
// moveTo()/lineTo()/closePath() (a polygon), beginPath(). Anything else
// the function calls is reported; the shapes recorded so far still count.
function recordClipFunc(fn, warnings) {
  const shapes = [];
  let polygon = null;
  const flush = () => { if (polygon && polygon.length >= 3) shapes.push({ kind: 'polygon', points: polygon }); polygon = null; };
  const ctx = new Proxy({}, {
    get(_t, name) {
      switch (name) {
        case 'beginPath': return () => { flush(); };
        case 'rect': return (x, y, w, h) => { flush(); shapes.push({ kind: 'rect', x, y, width: w, height: h }); };
        case 'arc': return (x, y, r, start, end, anticlockwise) => {
          flush();
          shapes.push({ kind: 'arc', x, y, radius: r, start_rad: start, end_rad: end, anticlockwise: !!anticlockwise });
        };
        case 'moveTo': return (x, y) => { flush(); polygon = [[x, y]]; };
        case 'lineTo': return (x, y) => { if (!polygon) polygon = []; polygon.push([x, y]); };
        case 'closePath': return () => { flush(); };
        case 'save': case 'restore': case 'clip': case 'fill': case 'stroke': return () => {};
        default:
          return (..._args) => { warnings.push(`clipFunc uses ctx.${String(name)} - not recorded`); };
      }
    },
  });
  try {
    fn(ctx);
  } catch (e) {
    warnings.push(`clipFunc threw: ${e && e.message ? e.message : e}`);
  }
  flush();
  return shapes;
}

function normalizeNode(node, warnings) {
  if (node === null || node === undefined || typeof node !== 'object') return [];
  if (Array.isArray(node)) return node.flatMap((n) => normalizeNode(n, warnings));
  const { type, props = {}, children = [] } = node;
  if (typeof type === 'function') {
    // A nested component (a shared sub-drawing) - call it like React would.
    return normalizeNode(type({ ...props, children }), warnings);
  }
  if (type === 'Fragment' || type === undefined) return children.flatMap((c) => normalizeNode(c, warnings));
  if (!PRIMITIVES.has(type)) {
    warnings.push(`unsupported primitive <${String(type)}>`);
    return [{ primitive: String(type), unsupported: true }];
  }
  const out = { primitive: type.toLowerCase() };
  for (const [key, value] of Object.entries(props)) {
    if (DROPPED_PROPS.has(key) || key.startsWith('on')) continue;
    if (key === 'clipFunc' && typeof value === 'function') {
      // A Konva clipFunc draws a clip path on a canvas context. It is
      // run once here against a recording context, and what it drew
      // (rects, arcs, polylines) is exported as the node's `clip` - the
      // runtime intersects its clip region with those shapes.
      const shapes = recordClipFunc(value, warnings);
      if (shapes.length) out.clip = shapes;
      continue;
    }
    if (typeof value === 'function') {
      warnings.push(`<${type}> prop ${key} is a function - not exportable`);
      out.unsupported_props = [...(out.unsupported_props || []), key];
      continue;
    }
    if (value === undefined) continue;
    out[key] = value;
  }
  if (type === 'Group') out.children = children.flatMap((c) => normalizeNode(c, warnings));
  else if (children.length) warnings.push(`<${type}> has children - ignored`);
  return [out];
}

// Merges the sentinel pass with the empty-fields pass: any prop that
// differs becomes a marker carrying the template and the empty-field
// default. Structure is expected to be identical; where it is not, the
// sentinel tree wins and the difference is reported.
const SENTINEL_RE = /\{\{[a-zA-Z]+\}\}/;
function mergeTrees(withSentinels, withDefaults, warnings, where = 'root') {
  if (withSentinels.length !== withDefaults.length) {
    warnings.push(`${where}: structure differs between sentinel and default pass (${withSentinels.length} vs ${withDefaults.length} nodes)`);
    return withSentinels;
  }
  return withSentinels.map((node, i) => {
    const other = withDefaults[i];
    const merged = {};
    for (const [key, value] of Object.entries(node)) {
      if (key === 'children') {
        merged.children = mergeTrees(value, other.children || [], warnings, `${where}/${node.primitive}[${i}]`);
      } else if (typeof value === 'string' && SENTINEL_RE.test(value)) {
        merged[key] = { $template: value, $default: other[key] === undefined ? null : other[key] };
      } else if (typeof value === 'number' && value === FONT_SIZE_SENTINEL) {
        merged[key] = { $template: '{{fontSize}}', $default: other[key] === undefined ? null : other[key] };
      } else if (typeof value === 'number' && other[key] !== undefined && typeof other[key] === 'number'
                 && value !== other[key]) {
        // A size derived from fontSize (a line height, a text box, a
        // label frame sized to its text): scaled from the sentinel, and
        // the empty-field default when the object sets no font size.
        merged[key] = { $template: '{{fontSize}}', $scale: value / FONT_SIZE_SENTINEL, $default: other[key] };
      } else {
        merged[key] = value;
      }
    }
    return merged;
  });
}

function resolveSymbolFile(file) {
  const base = path.join(SYMBOLS_DIR, file);
  for (const candidate of [base, base + '.tsx', base + '.ts']) {
    if (fs.existsSync(candidate) && fs.statSync(candidate).isFile()) return candidate;
  }
  throw new Error(`symbol source not found for ${file}`);
}

// Walks the merged tree next to the plain and the perturbed pass: a node
// whose `rotation` differs between the two is what the symbol animates.
// Structure is expected identical; where it is not, nothing is marked.
function markRotating(merged, plain, perturbed, warnings) {
  if (!Array.isArray(plain) || !Array.isArray(perturbed) || plain.length !== perturbed.length || merged.length !== plain.length) {
    warnings.push('rotation pass: structure differs - no rotating node marked');
    return merged;
  }
  let marked = 0;
  const walk = (m, a, b) => {
    for (let i = 0; i < m.length; i++) {
      const ra = a[i] && a[i].rotation, rb = b[i] && b[i].rotation;
      if (typeof ra === 'number' && typeof rb === 'number' && ra !== rb) { m[i].$animate_rotation = true; marked++; }
      if (m[i].children && a[i].children && b[i].children) walk(m[i].children, a[i].children, b[i].children);
    }
  };
  walk(merged, plain, perturbed);
  if (!marked) warnings.push('rotation pass: no node changed its rotation - base pose only');
  return merged;
}

function detectAnimation(type, file) {
  if (ANIMATION_DIRECTIVES[type]) return ANIMATION_DIRECTIVES[type];
  if (!file) return null;
  const source = fs.readFileSync(resolveSymbolFile(file), 'utf-8');
  if (/dashOffset/.test(source) && /requestAnimationFrame|setInterval/.test(source)) {
    return { type: 'dash_march', trigger_state: /'LIVE'/.test(source) ? 'LIVE' : 'ON', rate_px_per_sec: 30, note: 'auto-detected: dashOffset advanced per frame in source' };
  }
  if (/requestAnimationFrame|setInterval/.test(source)) {
    return { type: 'unknown', note: 'source animates (timer/rAF) but no directive is recorded - base pose exported' };
  }
  return null;
}

async function main() {
  const { SYMBOL_REGISTRY } = await import(pathToFileURL(path.join(SYMBOLS_DIR, 'SymbolRegistry.ts')).href);
  const dispatch = readDispatchTable();
  const components = await bundleComponents(dispatch);

  const symbols = {};
  const report = { exported: 0, generic: 0, failed: 0, warnings: 0 };
  for (const [type, def] of Object.entries(SYMBOL_REGISTRY)) {
    const entry = dispatch.get(type);
    const component = components[type];
    const w = def.defaultWidth, h = def.defaultHeight;
    const states = [...new Set([...(def.allowedStates || []), def.defaultState || 'NORMAL', 'NORMAL'])];
    const record = {
      label: def.label, category: def.category,
      reference_width: w, reference_height: h,
      allowed_states: def.allowedStates || [], default_state: def.defaultState || 'NORMAL',
      is_line: !!def.isLine, is_surface: !!def.isSurface, resize_redraws: !!def.resizeRedraws,
      designation_prefix: def.designationPrefix || null,
      terminals: (def.terminals || []).map((t) => ({ id: t.id, side: t.side, medium: t.medium || null })),
      connection_points: def.connectionPoints || [],
      component: entry ? entry.component : null,
      animation: detectAnimation(type, entry && entry.file),
      states: {},
      warnings: [],
    };
    if (!component) {
      // graphics.* and anything without a dedicated case: the editor's
      // GenericSymbol draws these (a box/circle + text) - the runtime has
      // its own generic drawing for exactly that.
      record.generic = true;
      report.generic++;
      symbols[type] = record;
      continue;
    }
    // A symbol with a WATER terminal draws its krociec in the colour of
    // the net it is on (SymbolRenderer.tsx passes terminalNetState) -
    // exported twice, all-INACTIVE and all-ACTIVE, so the runtime can
    // pick the variant once it has resolved the nets itself.
    const hasWaterTerminal = (def.terminals || []).some((t) => t.medium === 'WATER');
    if (hasWaterTerminal) record.states_net_active = {};
    const rotates = record.animation && record.animation.type === 'rotate';
    for (const state of states) {
      const warnings = [];
      try {
        const netInactive = () => 'INACTIVE';
        const netActive = () => 'ACTIVE';
        const render = (withSentinels, netState) => normalizeNode(
          component({ obj: fakeObject(type, def.category, w, h, state, withSentinels), state, terminalNetState: netState }),
          withSentinels ? warnings : []);
        const sentinelTree = render(true, netInactive);
        const defaultTree = render(false, netInactive);
        let tree = mergeTrees(sentinelTree, defaultTree, warnings);
        if (rotates && state === record.animation.trigger_state) {
          globalThis.__EPW_PERTURB_STATE = true;
          let perturbed;
          try { perturbed = render(false, netInactive); } finally { globalThis.__EPW_PERTURB_STATE = false; }
          tree = markRotating(tree, defaultTree, perturbed, warnings);
        }
        record.states[state] = tree;
        if (hasWaterTerminal) {
          record.states_net_active[state] = mergeTrees(render(true, netActive), render(false, netActive), warnings);
        }
      } catch (e) {
        record.states[state] = null;
        warnings.push(`export failed: ${e && e.message ? e.message : e}`);
      }
      for (const wmsg of new Set(warnings)) record.warnings.push(`${state}: ${wmsg}`);
    }
    if (Object.values(record.states).every((s) => s === null)) {
      record.export_error = record.warnings.join('; ');
      report.failed++;
    } else {
      report.exported++;
    }
    report.warnings += record.warnings.length;
    symbols[type] = record;
  }

  const output = {
    format: 'EPW_SYMBOL_GEOMETRY',
    schema_version: 1,
    generated_at: new Date().toISOString(),
    generated_by: 'studio/synoptic/tools/geometry_export/export.mjs',
    symbol_count: Object.keys(symbols).length,
    symbols,
  };
  fs.mkdirSync(path.dirname(OUT_FILE), { recursive: true });
  fs.writeFileSync(OUT_FILE, JSON.stringify(output, null, 1) + '\n', 'utf-8');
  console.log(`Wrote ${path.relative(REPO_ROOT, OUT_FILE)}: ${report.exported} exported, ${report.generic} generic, `
              + `${report.failed} failed, ${report.warnings} warning line(s).`);
  for (const [type, rec] of Object.entries(symbols)) {
    if (rec.warnings && rec.warnings.length) console.log(`  ${type}: ${rec.warnings.join(' | ')}`);
  }
  if (report.failed) process.exitCode = 1;
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
