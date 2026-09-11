#!/usr/bin/env node
// Renders the REAL, unmodified symbol components (studio/synoptic/src/
// symbols/**/*.tsx - the exact same source SymbolRenderer.tsx imports,
// bundled with esbuild for JSX only, no stubbing of react/react-konva
// this time) through the REAL rendering stack: real `react`, real
// `react-konva`, real `konva`, headless via node-canvas
// (`konva/canvas-backend`) - no browser, no dev server, but no
// approximation either. This is the strongest available "what the
// editor actually draws" reference for the spike's comparison (1.4) -
// NOT a screenshot of the running web app (that would need a browser/
// dev server this spike deliberately doesn't stand up), but the same
// engine, same component code, same draw calls.
//
// react-konva's own <Stage> component insists on a real DOM <div> (see
// its ReactKonvaCore.js - `container.current` comes from a React ref on
// a rendered 'div', which needs react-dom + a real DOM). Bypassed here
// by driving react-konva's exported reconciler (`KonvaRenderer`)
// directly against a manually-constructed Konva.Stage - no react-dom,
// no jsdom needed anywhere in this spike.
import esbuild from 'esbuild';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import fs from 'node:fs';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
require('konva/canvas-backend');
const Konva = require('konva').default;
const React = require('react');
const rk = require('react-konva');
const { ConcurrentRoot } = require('react-reconciler/constants');
const { createCanvas } = require('canvas');

// Node has no requestAnimationFrame - browser-only. Stubbed as a no-op
// (never actually schedules/advances anything) so FanSymbol's real
// useEffect (which calls it directly, unconditionally, when
// isRunning) doesn't throw. This intentionally freezes rotation at its
// own initial angle=0, same "geometry, not a random animation frame"
// intent as extract.mjs's React stub - see that file's own header.
global.requestAnimationFrame = () => 0;
global.cancelAnimationFrame = () => {};

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(HERE, '..', '..');
const SYMBOLS_DIR = path.join(REPO_ROOT, 'studio', 'synoptic', 'src', 'symbols');
const OUT_DIR = path.join(REPO_ROOT, 'shared', 'docs', 'spike');

const SCALE = 4; // upscale factor so 32-64px symbols are visible in a comparison image
const CELL_PAD = 44;
const LABEL_H = 22;

const TARGETS = [
  { type: 'electrical.circuit_breaker', file: 'electrical/CircuitBreakerSymbol.tsx', exportName: 'CircuitBreakerSymbol', w: 64, h: 64, states: ['OPEN', 'CLOSED', 'TRIPPED', 'FAULT'] },
  { type: 'electrical.indicator_lamp', file: 'electrical/IndicatorLampSymbol.tsx', exportName: 'IndicatorLampSymbol', w: 32, h: 32, states: ['OFF', 'ON', 'BLINK', 'FAULT'] },
  { type: 'hvac.fan', file: 'hvac/FanSymbol.tsx', exportName: 'FanSymbol', w: 64, h: 64, states: ['OFF', 'RUNNING', 'FAULT'] },
  { type: 'water.valve', file: 'water/ValveSymbol.tsx', exportName: 'ValveSymbol', w: 50, h: 40, states: ['CLOSED', 'OPENING', 'OPEN', 'CLOSING', 'FAULT'] },
];

async function loadRealComponent(target) {
  const result = await esbuild.build({
    entryPoints: [path.join(SYMBOLS_DIR, target.file)],
    bundle: true,
    write: false,
    format: 'cjs',
    platform: 'node',
    jsx: 'transform',
    jsxFactory: 'React.createElement',
    external: ['react', 'react-konva'], // use the REAL packages, not a stub
    logLevel: 'silent',
  });
  const outDir = path.join(HERE, '.bundled_real');
  fs.mkdirSync(outDir, { recursive: true });
  const outPath = path.join(outDir, target.type.replace(/\./g, '_') + '.cjs');
  fs.writeFileSync(outPath, result.outputFiles[0].text, 'utf-8');
  delete require.cache[require.resolve(outPath)];
  const mod = require(outPath);
  return mod[target.exportName];
}

function renderOneCell(Component, w, h, state) {
  const stage = new Konva.Stage({ width: w, height: h });
  const fiberRoot = rk.KonvaRenderer.createContainer(
    stage, ConcurrentRoot, null, false, null, '', console.error, console.error, console.error, null,
  );
  const element = React.createElement(
    rk.Layer, null,
    React.createElement(Component, { obj: { width: w, height: h, fill: '', border: '' }, state }),
  );
  rk.KonvaRenderer.updateContainer(element, fiberRoot, null);
  rk.KonvaRenderer.flushSyncWork();
  const canvas = stage.toCanvas({ pixelRatio: 1 });
  rk.KonvaRenderer.updateContainer(null, fiberRoot, null);
  stage.destroy();
  return canvas;
}

async function main() {
  const cellsPerRow = Math.max(...TARGETS.map((t) => t.states.length));
  const rowHeights = TARGETS.map((t) => t.h * SCALE + LABEL_H + CELL_PAD);
  const colWidth = Math.max(...TARGETS.map((t) => t.w * SCALE)) + CELL_PAD;

  const totalW = CELL_PAD + cellsPerRow * colWidth;
  const totalH = CELL_PAD + rowHeights.reduce((a, b) => a + b, 0);

  const composite = createCanvas(totalW, totalH);
  const ctx = composite.getContext('2d');
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, totalW, totalH);
  ctx.textBaseline = 'top';

  let y = CELL_PAD;
  for (const target of TARGETS) {
    const Component = await loadRealComponent(target);
    const cellW = target.w * SCALE;
    const cellH = target.h * SCALE;

    ctx.fillStyle = '#000000';
    ctx.font = 'bold 13px sans-serif';
    ctx.fillText(`${target.type}  (${target.w}x${target.h}, real Konva engine, real component code)`, CELL_PAD, y);

    let x = CELL_PAD;
    for (const state of target.states) {
      const cellCanvas = renderOneCell(Component, cellW, cellH, state);
      ctx.fillStyle = '#f0f0f0';
      ctx.fillRect(x, y + LABEL_H, cellW, cellH);
      ctx.drawImage(cellCanvas, x, y + LABEL_H);
      ctx.strokeStyle = '#cccccc';
      ctx.strokeRect(x, y + LABEL_H, cellW, cellH);
      ctx.fillStyle = '#333333';
      ctx.font = '11px sans-serif';
      ctx.fillText(state, x, y + LABEL_H + cellH + 2);
      x += colWidth;
    }
    y += target.h * SCALE + LABEL_H + CELL_PAD;
  }

  fs.mkdirSync(OUT_DIR, { recursive: true });
  const outPath = path.join(OUT_DIR, 'editor_reference.png');
  fs.writeFileSync(outPath, composite.toBuffer('image/png'));
  console.log('Wrote', outPath, `(${totalW}x${totalH})`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
