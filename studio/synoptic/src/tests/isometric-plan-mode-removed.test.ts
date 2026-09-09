// chore/remove-isometric-plan-mode - mandatory tests 10 and 11:
// 10. the src/iso directory does not exist.
// 11. no file imports anything from src/iso.
//
// Both read the source tree via Vite's own `import.meta.glob` (eager,
// `?raw`) rather than Node's `fs` - this tsconfig's own "types" list
// (tsconfig.app.json: `["vite/client"]`) has no Node globals at all
// (see help-consistency.test.ts's own comment on this same constraint),
// and `import.meta.glob` is the Vite-native equivalent of a recursive
// directory read, already fully typed under vite/client with no new
// dependency needed.

import { describe, it, expect } from 'vitest';

// Every .ts/.tsx file under src/, this test file's own sibling files
// included - eager+raw so the whole set is available synchronously,
// without needing any dynamic import/await gymnastics.
const allSourceFiles = import.meta.glob('../**/*.{ts,tsx}', { query: '?raw', import: 'default', eager: true }) as Record<string, string>;

describe('10. the src/iso directory does not exist', () => {
  it('no file anywhere under src/ resolves inside an iso/ directory', () => {
    const isoFiles = Object.keys(allSourceFiles).filter(path => /\/iso\//.test(path));
    expect(isoFiles).toEqual([]);
  });

  it('sanity: this glob actually sees real files (a passing empty-glob would prove nothing)', () => {
    expect(Object.keys(allSourceFiles).length).toBeGreaterThan(100);
  });
});

describe('11. no file imports anything from src/iso', () => {
  it('no source file\'s own import/require statement references an iso/ module', () => {
    const IMPORT_FROM_ISO = /from\s+['"][^'"]*\/iso\/[^'"]*['"]/;
    const offenders: string[] = [];
    for (const [path, source] of Object.entries(allSourceFiles)) {
      if (IMPORT_FROM_ISO.test(source)) offenders.push(path);
    }
    expect(offenders).toEqual([]);
  });

  it('sanity: the scan pattern actually catches an iso import (proves the test is not vacuously passing)', () => {
    const IMPORT_FROM_ISO = /from\s+['"][^'"]*\/iso\/[^'"]*['"]/;
    const contaminated = "import { TerrainTileType } from '../iso/TerrainTile';";
    expect(IMPORT_FROM_ISO.test(contaminated)).toBe(true);
  });
});
