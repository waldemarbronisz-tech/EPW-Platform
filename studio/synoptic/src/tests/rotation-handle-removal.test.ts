// fix/inline-device-creation commit 1: removes the free-rotation handle
// from every selection Transformer - a symbol only rotates in 90-degree
// steps (Properties' own Rotation field, or the R key) to keep its
// terminals on grid nodes, and a free drag of the rotate handle could
// misalign them.
//
// Konva cannot actually render in this project's jsdom test environment
// (no `canvas` npm package installed - see this file's own spike, kept
// out of the repo; every other test in src/tests/ already avoids
// mounting a Stage/Layer/Transformer for the same reason). So, mirroring
// the established "no hard-coded colors/fonts" convention (scada-
// symbols.test.ts, typography-proportions.test.ts - a ?raw source
// import plus a regex scan) this test verifies the Transformer configs
// statically instead of by rendering them.
import { describe, it, expect } from 'vitest';
import { useStore } from '../store';

import transformerHandlesSource from '../components/canvas/TransformerHandles.tsx?raw';
import groupCommandNodeSource from '../components/GroupCommandElementNode.tsx?raw';
import canvasSource from '../components/Canvas.tsx?raw';

// Pulls one exported component's own body out of the file's source so
// each element kind's Transformer config is checked independently
// rather than one regex matching whichever `rotateEnabled` happens to
// appear first in the file.
function extractComponentBody(source: string, exportName: string): string {
  const start = source.indexOf(`export const ${exportName}`);
  expect(start, `${exportName} not found in TransformerHandles.tsx`).toBeGreaterThanOrEqual(0);
  const nextExport = source.indexOf('\nexport const ', start + 1);
  return nextExport === -1 ? source.slice(start) : source.slice(start, nextExport);
}

describe('1. rotateEnabled is false on every schematic-mode selection Transformer', () => {
  it('ObjectTransformerHandle (symbol, and scada.boundary_point - both plain SynopticObject entries selected via selectedIds) disables rotation', () => {
    const body = extractComponentBody(transformerHandlesSource, 'ObjectTransformerHandle');
    expect(body).toMatch(/<Transformer[\s\S]*?rotateEnabled=\{false\}/);
  });

  it('FrameTransformerHandle (ramka) disables rotation', () => {
    const body = extractComponentBody(transformerHandlesSource, 'FrameTransformerHandle');
    expect(body).toMatch(/<Transformer[\s\S]*?rotateEnabled=\{false\}/);
  });

  it('WidthOnlyTransformerHandle (miernik, panel sygnalizacyjny, panel nastaw) disables rotation', () => {
    const body = extractComponentBody(transformerHandlesSource, 'WidthOnlyTransformerHandle');
    expect(body).toMatch(/<Transformer[\s\S]*?rotateEnabled=\{false\}/);
  });

  it('every Transformer in TransformerHandles.tsx sets rotateEnabled explicitly (no export left on Konva\'s own default)', () => {
    const transformerBlocks = transformerHandlesSource.split('<Transformer').slice(1);
    expect(transformerBlocks.length).toBeGreaterThanOrEqual(3);
    for (const block of transformerBlocks) {
      // Each Transformer's own props run up to its closing `/>`.
      const propsText = block.slice(0, block.indexOf('/>'));
      expect(propsText).toContain('rotateEnabled={false}');
    }
  });
});

describe('2. the one element kind with no Transformer at all (przycisk komendy grupowej) never had a rotate handle to begin with', () => {
  it('GroupCommandElementNode draws its own selection as a plain dashed shape, no Konva Transformer', () => {
    expect(groupCommandNodeSource).not.toMatch(/react-konva'[\s\S]*?Transformer/);
    expect(groupCommandNodeSource).not.toContain('<Transformer');
  });
});

describe('3. rotation stays available with the free-rotation handle gone: Properties\' Rotation field and the R key', () => {
  it('rotateSelected rotates the current selection by exactly 90 degrees per call, both directions', () => {
    useStore.setState({
      objects: [
        { id: 'o1', type: 'symbol', category: 'electrical', x: 0, y: 0, rotation: 0, scaleX: 1, scaleY: 1, visible: true, locked: false, layer: 0, tag: '', description: '', color: '', fill: '', border: '', text: '', font: '', fontSize: 12, customProperties: {}, width: 40, height: 40 } as any,
      ],
      selectedIds: ['o1'],
    });
    useStore.getState().rotateSelected('cw');
    expect(useStore.getState().objects[0].rotation).toBe(90);
    useStore.getState().rotateSelected('cw');
    expect(useStore.getState().objects[0].rotation).toBe(180);
    useStore.getState().rotateSelected('ccw');
    expect(useStore.getState().objects[0].rotation).toBe(90);
  });

  it('Canvas.tsx\'s own keydown handler still binds R/Shift+R to rotateSelected, unguarded by the wire/frame tool state so it works for a plain selection', () => {
    expect(canvasSource).toMatch(/e\.key\.toLowerCase\(\) === 'r'[\s\S]{0,900}rotateSelected\(e\.shiftKey \? 'ccw' : 'cw'\)/);
  });

  it('the rotateSelected store action both the R key and Properties\' Rotation-adjacent Toolbar buttons rely on is still exposed', () => {
    expect(typeof useStore.getState().rotateSelected).toBe('function');
  });
});
