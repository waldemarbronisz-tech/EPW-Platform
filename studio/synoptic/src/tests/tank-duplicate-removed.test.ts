// fix/tank-language-and-media commit 3 - the 3 mandatory tests for
// removing the duplicate rainwater tank from the library. Read via
// Vite's `?raw` suffix, not `fs.readFileSync` - this tsconfig's own
// "types" list is deliberately just ["vite/client"], so `node:fs`/
// `__dirname` do not resolve here at all (same fix
// water-management-example-project.test.ts's own header already
// documents).

import { describe, it, expect } from 'vitest';
import { getSymbolDefinition, getSymbolsByCategory } from '../symbols/SymbolRegistry';
import entryGateLibraryTest from '../../examples/ENTRY_GATE_LIBRARY_TEST.epwsyn?raw';
import gospodarkaWodna from '../../examples/GOSPODARKA_WODNA.epwsyn?raw';
import libraryTest from '../../examples/LIBRARY_TEST.epwsyn?raw';
import statefulSymbols from '../../examples/STATEFUL_SYMBOLS.epwsyn?raw';

const EXAMPLE_PROJECTS: Record<string, string> = {
  'ENTRY_GATE_LIBRARY_TEST.epwsyn': entryGateLibraryTest,
  'GOSPODARKA_WODNA.epwsyn': gospodarkaWodna,
  'LIBRARY_TEST.epwsyn': libraryTest,
  'STATEFUL_SYMBOLS.epwsyn': statefulSymbols
};

describe('14. the library contains exactly one rainwater tank', () => {
  it('site.rain_tank is hidden - only site.rainwater_tank2 appears in the visible Water group', () => {
    const water = getSymbolsByCategory()['Water'] || [];
    const tanks = water.filter(d => d.label === 'Rainwater Tank');
    expect(tanks.map(d => d.type)).toEqual(['site.rainwater_tank2']);
  });

  it('no visible category anywhere in the library offers a second tank under this label', () => {
    const allVisible = Object.values(getSymbolsByCategory()).flat();
    const tanks = allVisible.filter(d => d.label === 'Rainwater Tank');
    expect(tanks.length).toBe(1);
  });
});

describe('15. the removed symbol still exists in the code, marked hidden', () => {
  it('site.rain_tank\'s own registry entry is still fully defined (getSymbolDefinition never filters by hiddenFromLibrary - only the library UI does)', () => {
    const def = getSymbolDefinition('site.rain_tank');
    expect(def).toBeDefined();
    expect(def!.hiddenFromLibrary).toBe(true);
    expect(def!.terminals).toEqual([{ id: 'KROCIEC', side: 'RIGHT', medium: 'WATER' }]);
  });

  it('RainTankSymbol.tsx (the component file itself) was not deleted', async () => {
    const source = (await import('../symbols/site/RainTankSymbol.tsx?raw')).default;
    expect(source.length).toBeGreaterThan(0);
    expect(source).toContain('RainTankSymbol');
  });
});

describe('16. no example project references the removed symbol', () => {
  it('none of the four examples/ project files contain the string site.rain_tank', () => {
    for (const [name, source] of Object.entries(EXAMPLE_PROJECTS)) {
      expect(source, `${name} should not reference site.rain_tank`).not.toContain('site.rain_tank');
    }
  });

  it('sanity: at least one example already uses the surviving tank (site.rainwater_tank2), so this scan is exercising real content, not an empty file', () => {
    expect(gospodarkaWodna).toContain('site.rainwater_tank2');
  });
});
