// One icon look everywhere in EPW Studio: the Synoptic editor's toolbar and
// format bar draw the Studio shell's own pixel icons (generated into
// studioIconData.ts), not a separate line-icon set.

import { describe, it, expect } from 'vitest';
import { STUDIO_ICONS } from '../components/icons/studioIconData';

import toolbarSource from '../components/Toolbar.tsx?raw';
import formatBarSource from '../components/FormatBar.tsx?raw';

const namesUsed = (source: string) => [
  ...Array.from(source.matchAll(/<StudioIcon name="([a-z_]+)"/g), m => m[1]),
  ...Array.from(source.matchAll(/icon: '([a-z_]+)'/g), m => m[1]),
];

describe('Studio pixel icons in the Synoptic editor', () => {
  it('the toolbar and the format bar no longer use the line-icon library', () => {
    expect(toolbarSource).not.toContain("from 'lucide-react'");
    expect(formatBarSource).not.toContain("from 'lucide-react'");
  });

  it('every icon they name exists in the generated Studio icon data', () => {
    const used = [...namesUsed(toolbarSource), ...namesUsed(formatBarSource)];
    expect(used.length).toBeGreaterThan(25);
    for (const name of used) {
      expect(STUDIO_ICONS[name], name).toBeTruthy();
    }
  });

  it('every icon is a full 16 x 16 raised tile, like the electricity and water icons', () => {
    for (const [name, data] of Object.entries(STUDIO_ICONS)) {
      const runs = data.split(';').map(r => r.split(','));
      // top-left pixel of the tile edge is white, bottom-right is dark grey
      const topLeft = runs.find(([x, y]) => x === '0' && y === '0');
      const lastRow = runs.filter(([, y]) => y === '15');
      expect(topLeft, name).toBeTruthy();
      expect(lastRow.length, name).toBeGreaterThan(0);
    }
  });
});
