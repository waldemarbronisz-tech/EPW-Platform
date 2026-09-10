#!/usr/bin/env node
// SPIKE - geometry export prototype for Path C (SYMBOL_RENDERING_PATHS.md).
// Not production code, not wired into the runtime or the editor build.
//
// WHAT THIS DOES: for 4 representative symbols, executes the REAL
// component file from studio/synoptic/src/symbols/**/*.tsx as a plain
// function - not through react-konva's actual renderer (that needs a
// real Konva.Stage, which needs a canvas backend Node doesn't have
// without native bindings) - by bundling each file with esbuild
// (JSX -> React.createElement calls) against two tiny local stub
// modules (stubs/react.js, stubs/react-konva.js) instead of the real
// packages. Calling the resulting function directly returns a plain
// {type, props, children} tree - exactly the JSX the component would
// have built for a real render, just never handed to an actual
// renderer. That tree is then walked and normalized (0..1 fractions of
// the symbol's own width/height) into geometry_sample.json.
//
// See stubs/react.js's own header for exactly how useState/useEffect
// are stubbed (freezes every symbol at its OWN declared initial pose -
// this is what makes animated symbols export a static BASE geometry
// instead of one random animation frame).
//
// Animation itself is never extracted from tracing timer behavior -
// ANIMATION_DIRECTIVES below is a small, HAND-AUTHORED table (read
// from the real setInterval/requestAnimationFrame calls in source, see
// each entry's own `note`), because the task's own framing is explicit:
// "Animacja NIE jest geometria... eksport ma zawierac dyrektywe."

import esbuild from 'esbuild';
import { register } from 'node:module';
import { pathToFileURL, fileURLToPath } from 'node:url';
import path from 'node:path';
import fs from 'node:fs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(HERE, '..', '..');
const SYMBOLS_DIR = path.join(REPO_ROOT, 'studio', 'synoptic', 'src', 'symbols');
const BUNDLED_DIR = path.join(HERE, '.bundled');

register(pathToFileURL(path.join(HERE, 'resolve_ts_ext.mjs')).href, import.meta.url);

// --- The 4 targets, exactly as named in the task prompt - all 4 exist
// under exactly those names, no substitution needed. --------------------

const TARGETS = [
  {
    type: 'electrical.circuit_breaker',
    file: 'electrical/CircuitBreakerSymbol.tsx',
    exportName: 'CircuitBreakerSymbol',
    difficulty: 'a) purely static, multi-state',
  },
  {
    type: 'electrical.indicator_lamp',
    file: 'electrical/IndicatorLampSymbol.tsx',
    exportName: 'IndicatorLampSymbol',
    difficulty: 'b) animated - blink',
  },
  {
    type: 'hvac.fan',
    file: 'hvac/FanSymbol.tsx',
    exportName: 'FanSymbol',
    difficulty: 'c) animated - rotation',
  },
  {
    type: 'water.valve',
    file: 'water/ValveSymbol.tsx',
    exportName: 'ValveSymbol',
    difficulty: 'd) terminals + multiple states',
  },
];

// Hand-authored, not auto-derived - see file header. Every field is
// either ZMIERZONE (read verbatim from a fixed constant in source) or
// explicitly marked measured:false with a `note` explaining why it
// isn't (see hvac.fan below - its "rate" is coupled to the browser's
// frame rate, not a fixed number in source at all).
const ANIMATION_DIRECTIVES = {
  'electrical.indicator_lamp': {
    type: 'blink',
    trigger_state: 'BLINK',
    half_period_ms: 500,
    measured: true,
    note: "IndicatorLampSymbol.tsx: setInterval(() => setBlinkOn(b => !b), 500) - an explicit, fixed constant in source.",
  },
  'hvac.fan': {
    type: 'rotate',
    trigger_state: 'RUNNING',
    rate_deg_per_sec: 900,
    measured: false,
    note: "FanSymbol.tsx increments its angle by 15deg per requestAnimationFrame callback, not per fixed time unit - " +
          "real-world speed is coupled to the browser's display refresh rate (typically ~60Hz), which is NOT a " +
          "constant recorded anywhere in source. 900deg/s (=150rpm) here ASSUMES 60fps - this is the one animation " +
          "number in this export that is genuinely an assumption, not a measurement.",
  },
};

function norm(v, ref) {
  if (v === undefined || v === null) return 0;
  if (typeof v !== 'number' || !isFinite(ref) || ref === 0) return v;
  return v / ref;
}

// Handles exactly the path grammar this codebase's own Path shapes use
// for the 4 targets in this spike (absolute M/L/Z only - confirmed by
// reading every Path in these 4 files' full import graph before writing
// this). Any other command is left un-normalized and flagged - an
// honest limitation, not a silent wrong answer.
function normalizePathData(d, w, h) {
  if (typeof d !== 'string') return { ok: false, reason: 'no path data string' };
  const tokens = d.match(/[MLZmlz]|-?\d*\.?\d+(?:e-?\d+)?/gi);
  if (!tokens) return { ok: false, reason: 'unparseable path data' };
  let out = '';
  let cmd = null;
  let coordIndex = 0; // 0 = x axis (divide by w), 1 = y axis (divide by h)
  for (const tok of tokens) {
    if (/^[mlz]$/i.test(tok)) {
      if (tok !== tok.toUpperCase()) {
        return { ok: false, reason: `relative command '${tok}' not supported by this spike's normalizer` };
      }
      cmd = tok.toUpperCase();
      coordIndex = 0;
      out += (out ? ' ' : '') + cmd;
      continue;
    }
    if (cmd !== 'M' && cmd !== 'L') {
      return { ok: false, reason: `unsupported path command context near token '${tok}'` };
    }
    const num = parseFloat(tok);
    const ref = coordIndex === 0 ? w : h;
    out += ' ' + (num / ref);
    coordIndex = 1 - coordIndex;
  }
  return { ok: true, data: out.trim() };
}

// Walks the plain-object element tree stubs/react.js's createElement()
// produced, converting each Konva primitive into a normalized (0..1)
// shape description. Anything not explicitly handled is recorded as
// `unsupported: true` with its raw props preserved - never silently
// dropped, so a real gap shows up in the output, not just in a log.
function normalizeNode(node, w, h) {
  if (!node || typeof node !== 'object' || !node.type) return null;
  const { type, props = {}, children = [] } = node;
  const common = {};
  if ('fill' in props) common.fill = props.fill;
  if ('stroke' in props) common.stroke = props.stroke;
  if ('strokeWidth' in props) common.strokeWidth = props.strokeWidth;
  if ('dash' in props) common.dash = props.dash;
  if ('opacity' in props) common.opacity = props.opacity;
  if ('listening' in props) common.listening = props.listening;

  switch (type) {
    case 'Group': {
      const out = { primitive: 'group', ...common };
      if ('x' in props) out.x = norm(props.x, w);
      if ('y' in props) out.y = norm(props.y, h);
      if ('rotation' in props) out.rotation_deg = props.rotation;
      out.children = children.map((c) => normalizeNode(c, w, h)).filter(Boolean);
      return out;
    }
    case 'Rect':
      return {
        primitive: 'rect', ...common,
        x: norm(props.x ?? 0, w), y: norm(props.y ?? 0, h),
        width: norm(props.width ?? 0, w), height: norm(props.height ?? 0, h),
      };
    case 'Circle':
      return {
        primitive: 'circle', ...common,
        x: norm(props.x, w), y: norm(props.y, h),
        radius: norm(props.radius, w),
      };
    case 'Line':
      return {
        primitive: 'line', ...common,
        points: (props.points || []).map((v, i) => norm(v, i % 2 === 0 ? w : h)),
      };
    case 'Arc':
      return {
        primitive: 'arc', ...common,
        x: norm(props.x, w), y: norm(props.y, h),
        inner_radius: norm(props.innerRadius, w), outer_radius: norm(props.outerRadius, w),
        angle_deg: props.angle, rotation_deg: props.rotation,
      };
    case 'Path': {
      const result = normalizePathData(props.data, w, h);
      const out = { primitive: 'path', ...common, data_raw: props.data };
      if (result.ok) out.data_normalized = result.data;
      else out.normalization_warning = result.reason;
      return out;
    }
    case 'Text':
      return {
        primitive: 'text', ...common,
        x: norm(props.x ?? 0, w), y: norm(props.y ?? 0, h),
        width: props.width != null ? norm(props.width, w) : undefined,
        height: props.height != null ? norm(props.height, h) : undefined,
        text: props.text, font_size_px: props.fontSize,
      };
    default:
      return { primitive: type, unsupported: true, raw_props: props };
  }
}

async function bundleComponent(target) {
  const entry = path.join(SYMBOLS_DIR, target.file);
  const result = await esbuild.build({
    entryPoints: [entry],
    bundle: true,
    write: false,
    format: 'esm',
    platform: 'neutral',
    jsx: 'transform',
    jsxFactory: 'React.createElement',
    jsxFragment: 'React.Fragment',
    alias: {
      react: path.join(HERE, 'stubs', 'react.js'),
      'react-konva': path.join(HERE, 'stubs', 'react-konva.js'),
    },
    logLevel: 'silent',
  });
  fs.mkdirSync(BUNDLED_DIR, { recursive: true });
  const outPath = path.join(BUNDLED_DIR, target.type.replace(/\./g, '_') + '.mjs');
  fs.writeFileSync(outPath, result.outputFiles[0].text, 'utf-8');
  // Cache-busting query so re-running this script picks up source edits.
  const mod = await import(pathToFileURL(outPath).href + '?t=' + Date.now());
  const componentFn = mod[target.exportName];
  if (typeof componentFn !== 'function') {
    throw new Error(`${target.file} did not export a function named '${target.exportName}'`);
  }
  return componentFn;
}

async function main() {
  register(pathToFileURL(path.join(HERE, 'resolve_ts_ext.mjs')).href, import.meta.url);
  const { SYMBOL_REGISTRY } = await import(
    pathToFileURL(path.join(SYMBOLS_DIR, 'SymbolRegistry.ts')).href
  );

  const symbols = {};
  const timings = {};

  for (const target of TARGETS) {
    const t0 = performance.now();
    const def = SYMBOL_REGISTRY[target.type];
    if (!def) throw new Error(`'${target.type}' not found in SYMBOL_REGISTRY - has it been renamed?`);

    const componentFn = await bundleComponent(target);
    const w = def.defaultWidth;
    const h = def.defaultHeight;

    const states = {};
    for (const state of def.allowedStates) {
      const fakeObj = { width: w, height: h, fill: '', border: '', text: '', font: '', fontSize: 0 };
      const tree = componentFn({ obj: fakeObj, state, terminalNetState: undefined });
      states[state] = normalizeNode(tree, w, h);
    }

    symbols[target.type] = {
      label: def.label,
      category: def.category,
      difficulty_class: target.difficulty,
      reference_width: w,
      reference_height: h,
      allowed_states: def.allowedStates,
      terminal_count: (def.terminals || []).length,
      animation: ANIMATION_DIRECTIVES[target.type] || null,
      states,
    };
    timings[target.type] = performance.now() - t0;
  }

  const output = {
    generated_at: new Date().toISOString(),
    generated_by: 'spike/geometry_export/extract.mjs',
    method: 'Executes the real .tsx component as a plain function (esbuild JSX transform against ' +
            'stub react/react-konva modules - see stubs/*.js) - never a real Konva/canvas render. ' +
            'useState/useEffect are stubbed to freeze each symbol at its own declared initial pose; ' +
            'animation is a hand-authored directive (ANIMATION_DIRECTIVES in this script), not traced.',
    extraction_time_ms: timings,
    symbols,
  };

  fs.writeFileSync(
    path.join(REPO_ROOT, 'shared', 'docs', 'spike', 'geometry_sample.json'),
    JSON.stringify(output, null, 2) + '\n',
    'utf-8',
  );
  console.log('Wrote geometry_sample.json.');
  console.log('Extraction time per symbol (ms):', timings);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
