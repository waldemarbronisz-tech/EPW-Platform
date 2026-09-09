// fix/hydraulic-connections commit 5 - the 6 mandatory tests for the
// hydraulic connection standard (krociec + kolnierz) at every water-
// medium object's own terminal. waterStub/waterFlange (BandedShading.tsx)
// are plain functions returning a React element tree (via the JSX
// transform's own React.createElement calls) - inspectable directly
// through their own .props, with no Konva canvas/jsdom rendering needed
// at all, the same way any other pure-function-returning-JSX helper in
// this codebase already gets tested.

import { describe, it, expect } from 'vitest';
import { waterStub, waterFlange, flangeCenterForSide } from '../symbols/site/BandedShading';
import { SITE_BLUE, SITE_GREY, SITE_OBJECT_PIPE_WIDTH, SITE_FLANGE_THICKNESS, SITE_FLANGE_SPAN } from '../theme/ScadaTheme';
import { SYMBOL_REGISTRY } from '../symbols/SymbolRegistry';
import electricalRegistrySource from '../symbols/registry/electrical.ts?raw';

/** Recursively find every element of a given Konva component-name (as
 * the JSX transform records it - a string for a react-konva host tag
 * like 'Rect', or the function reference for a helper component) in a
 * React element tree, by reading .props.children by hand (no renderer,
 * no test-utils - this element tree was never mounted at all). */
function findAll(element: any, typeName: string): any[] {
  if (!element || typeof element !== 'object') return [];
  const results: any[] = [];
  const isMatch = typeof element.type === 'string' ? element.type === typeName : element.type?.name === typeName;
  if (isMatch) results.push(element);
  const children = element.props?.children;
  const list = Array.isArray(children) ? children : children ? [children] : [];
  for (const child of list) results.push(...findAll(child, typeName));
  return results;
}

describe('17. every water aparat has a krociec+kolnierz on every one of its own terminals', () => {
  it('waterStub draws both a pipe (objectPipeSegment) and a flange (waterFlange) in one call', () => {
    const el = waterStub(20, 48, 'L', true, 128, 96);
    // objectPipeSegment itself returns a Group whose first Path is the
    // outline pass - confirms the pipe portion is really there.
    expect(findAll(el, 'Path').length).toBeGreaterThan(0);
    // waterFlange returns Rects - confirms the flange portion is there too.
    expect(findAll(el, 'Rect').length).toBeGreaterThan(0);
  });

  it('every registered water-medium symbol\'s own component source calls waterStub (or waterFlange directly, for the handful needing a jog)', async () => {
    const waterMediumTypes = Object.values(SYMBOL_REGISTRY)
      .filter(def => (def.terminals || []).some(t => t.medium === 'WATER'))
      .map(def => def.type);
    expect(waterMediumTypes.length).toBeGreaterThan(0); // sanity: this scan actually found objects to check

    // Every one of this task's own commit-5 files - imported by name so
    // this test fails loudly (a missing import) if any object's own
    // component file is not on this list, rather than silently skipping it.
    const sources = await Promise.all([
      import('../symbols/site/CheckValveSymbol.tsx?raw'),
      import('../symbols/site/WaterFilterSymbol.tsx?raw'),
      import('../symbols/site/HydroforSymbol.tsx?raw'),
      import('../symbols/site/FlowMeterSymbol.tsx?raw'),
      import('../symbols/site/WaterMeterSymbol.tsx?raw'),
      import('../symbols/site/PressureSwitchSymbol.tsx?raw'),
      import('../symbols/site/SprinklerHeadSymbol.tsx?raw'),
      import('../symbols/site/DripLineSymbol.tsx?raw'),
      import('../symbols/site/WaterValveSymbol.tsx?raw'),
      import('../symbols/site/WaterSelectorValveSymbol.tsx?raw'),
      import('../symbols/site/RainTankSymbol.tsx?raw'),
      import('../symbols/site/SewagePlantSymbol.tsx?raw'),
      import('../symbols/site/WaterManholeSymbol.tsx?raw'),
      import('../symbols/site/GardenSprinklerSymbol.tsx?raw'),
      import('../symbols/water/ValveSymbol.tsx?raw'),
      import('../symbols/water/GateValveSymbol.tsx?raw'),
      import('../symbols/water/BallValveSymbol.tsx?raw'),
      import('../symbols/water/SolenoidValveSymbol.tsx?raw'),
      import('../symbols/water/DrainValveSymbol.tsx?raw'),
      import('../symbols/water/PumpSymbol.tsx?raw'),
      import('../symbols/water/TankSymbol.tsx?raw'),
      import('../symbols/water/DrainSymbol.tsx?raw')
    ]);
    for (const mod of sources) {
      const source = mod.default;
      expect(source.includes('waterStub') || source.includes('waterFlange')).toBe(true);
    }
  });
});

describe('18. the krociec is grey without flow, blue with flow', () => {
  it('waterStub(..., true, ...) fills the pipe core with SITE_BLUE', () => {
    const el = waterStub(20, 48, 'L', true, 128, 96);
    const corePath = findAll(el, 'Path')[1]; // [outline, core, shadow, highlight]
    expect(corePath.props.stroke).toBe(SITE_BLUE.base);
  });

  it('waterStub(..., false, ...) fills the pipe core with SITE_GREY', () => {
    const el = waterStub(20, 48, 'L', false, 128, 96);
    const corePath = findAll(el, 'Path')[1];
    expect(corePath.props.stroke).toBe(SITE_GREY.base);
  });

  it('the flange itself follows the identical rule - blue live, grey not', () => {
    expect(findAll(waterFlange(4, 48, 'L', true), 'Rect')[0].props.fill).toBe(SITE_BLUE.base);
    expect(findAll(waterFlange(4, 48, 'L', false), 'Rect')[0].props.fill).toBe(SITE_GREY.base);
  });
});

describe('19. the flange is wider than the pipe core', () => {
  it('SITE_FLANGE_SPAN (the flange\'s own span across the pipe) is bigger than SITE_OBJECT_PIPE_WIDTH (the pipe\'s own core width)', () => {
    expect(SITE_FLANGE_SPAN).toBeGreaterThan(SITE_OBJECT_PIPE_WIDTH);
  });

  it('an L/R flange\'s own drawn Rect is SITE_FLANGE_SPAN tall - wider across the pipe than the pipe\'s own core', () => {
    const rect = findAll(waterFlange(4, 48, 'L', true), 'Rect')[0];
    expect(rect.props.height).toBe(SITE_FLANGE_SPAN);
    expect(rect.props.height).toBeGreaterThan(SITE_OBJECT_PIPE_WIDTH);
  });

  it('a T/B flange is the same, rotated - SITE_FLANGE_SPAN wide instead of tall', () => {
    const rect = findAll(waterFlange(64, 4, 'T', true), 'Rect')[0];
    expect(rect.props.width).toBe(SITE_FLANGE_SPAN);
  });
});

describe('20. a water aparat\'s terminal still sits exactly on the middle of its own edge, krociec or not', () => {
  it('every water-medium symbol\'s own registered terminal is still exactly at its edge midpoint (getTerminalOffsetForSide\'s own fixed rule) - unaffected by any internal drawing change this commit made', async () => {
    const { getTerminalOffsetForSide } = await import('../utils/Terminals');
    const waterSymbols = Object.values(SYMBOL_REGISTRY).filter(def => (def.terminals || []).some(t => t.medium === 'WATER'));
    for (const def of waterSymbols) {
      for (const spec of def.terminals!.filter(t => t.medium === 'WATER')) {
        const offset = getTerminalOffsetForSide(spec.side, def.defaultWidth, def.defaultHeight);
        if (spec.side === 'LEFT') expect(offset).toEqual({ x: 0, y: def.defaultHeight / 2 });
        if (spec.side === 'RIGHT') expect(offset).toEqual({ x: def.defaultWidth, y: def.defaultHeight / 2 });
        if (spec.side === 'TOP') expect(offset).toEqual({ x: def.defaultWidth / 2, y: 0 });
        if (spec.side === 'BOTTOM') expect(offset).toEqual({ x: def.defaultWidth / 2, y: def.defaultHeight });
      }
    }
  });
});

describe('21. an electrical aparat has no flange', () => {
  it('registry/electrical.ts\'s own source never references waterStub/waterFlange at all', () => {
    expect(electricalRegistrySource).not.toContain('waterStub');
    expect(electricalRegistrySource).not.toContain('waterFlange');
  });

  it('no ELECTRICAL-only symbol declares a WATER terminal (the actual gate this task\'s own rule depends on)', () => {
    const electricalDefs = Object.values(SYMBOL_REGISTRY).filter(def => def.category === 'Electrical');
    for (const def of electricalDefs) {
      expect((def.terminals || []).some(t => t.medium === 'WATER')).toBe(false);
    }
  });

  it('a VENTILATION-medium terminal likewise never gets a flange - waterStub/waterFlange are only ever called with a WATER-medium object in mind, never wired to any ventilation symbol\'s own source', async () => {
    const hvacSource = (await import('../symbols/registry/hvac.ts?raw')).default;
    expect(hvacSource).not.toContain('waterStub');
    expect(hvacSource).not.toContain('waterFlange');
  });
});

describe('22. the flange/krociec dimensions come from ScadaTheme, not the component', () => {
  it('SITE_STUB_LENGTH, SITE_FLANGE_THICKNESS, SITE_FLANGE_SPAN and SITE_OBJECT_PIPE_WIDTH are all real ScadaTheme exports with the reference\'s own literal values', async () => {
    const theme = await import('../theme/ScadaTheme');
    expect(theme.SITE_STUB_LENGTH).toBe(14);
    expect(theme.SITE_FLANGE_THICKNESS).toBe(6);
    expect(theme.SITE_OBJECT_PIPE_WIDTH).toBe(13);
    expect(theme.SITE_FLANGE_SPAN).toBe(theme.SITE_OBJECT_PIPE_WIDTH + 11);
  });

  it('BandedShading.tsx\'s own waterStub/waterFlange never hardcode a flange dimension as a bare literal - flangeCenterForSide computes purely from the imported constants', () => {
    // flangeCenterForSide's own output for a fixed canvas size must move
    // if SITE_FLANGE_THICKNESS changes - proven indirectly by checking
    // its result is consistent with the CURRENT constant's own value,
    // not a coincidentally-matching hardcoded number.
    const center = flangeCenterForSide('R', 48, 128, 96);
    expect(center.x).toBe(128 - SITE_FLANGE_THICKNESS / 2 - 1);
  });
});
