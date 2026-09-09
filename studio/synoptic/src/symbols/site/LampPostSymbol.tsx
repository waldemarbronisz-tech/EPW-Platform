// feat/site-objects-2d commit 3 - "6. Slup oswietleniowy, dwie oprawy"
// and "7. Slup oswietleniowy, jedna oprawa" from
// docs/EPW_rysunki_referencja.py's own slup(n,on) - the SAME drawing
// function there, parametrized by a fixture count (2 or 1), so both
// live in this one file sharing the actual render logic (renderLampPost
// below), each exported as its own named component/state list to keep
// the established "one file per symbol" registration pattern for
// everything ELSE (registry entry, SymbolRenderer case, tests).

import React from 'react';
import { Group, Line } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { bandedRect, bandedVRect, glow } from './BandedShading';
import { resolveSiteState } from './SiteSymbolState';
import {
  COLOR_OUTLINE, SITE_CONC, SITE_DGREY, SITE_YELL, SITE_DARK,
  SITE_BAND_WIDTH_NARROW, SITE_OUTLINE_WIDTH, SITE_OUTLINE_WIDTH_MEDIUM, SITE_CROSSBAR_WIDTH, SITE_CROSSBAR_HIGHLIGHT,
  SITE_CANVAS_SCALE
} from '../../theme/ScadaTheme';

export type LampPostState = 'ZALACZONY' | 'WYLACZONY';
// oxlint-disable-next-line react/only-export-components -- one file per symbol pair, same convention as scada/ symbols.
export const LAMP_POST_STATES: LampPostState[] = ['ZALACZONY', 'WYLACZONY'];

function renderLampPost(fixtureCount: 1 | 2, on: boolean): React.ReactElement {
  const fixtureColor = on ? SITE_YELL : SITE_DARK;
  const crossbar = fixtureCount === 2
    ? { x1: 30, y1: 26, x2: 130, y2: 26 }
    : { x1: 80, y1: 26, x2: 124, y2: 26 };

  return (
    // SITE_CANVAS_SCALE - see HouseSymbol.tsx's own comment on this
    // same wrapper for the full reasoning.
    <Group scaleX={SITE_CANVAS_SCALE} scaleY={SITE_CANVAS_SCALE}>
      {bandedRect(72, 88, 16, 18, SITE_CONC, { band: SITE_BAND_WIDTH_NARROW, outlineWidth: SITE_OUTLINE_WIDTH_MEDIUM })}
      {bandedVRect(75, 26, 10, 64, SITE_DGREY, { band: SITE_BAND_WIDTH_NARROW })}
      <Line points={[crossbar.x1, crossbar.y1, crossbar.x2, crossbar.y2]} stroke={COLOR_OUTLINE} strokeWidth={SITE_CROSSBAR_WIDTH} lineCap="round" />
      <Line points={[crossbar.x1, crossbar.y1 - 1, crossbar.x2, crossbar.y2 - 1]} stroke={SITE_CROSSBAR_HIGHLIGHT} strokeWidth={SITE_OUTLINE_WIDTH} lineCap="round" listening={false} />
      {fixtureCount === 2 ? (
        <>
          {[30, 130].map(x => (
            <Group key={x}>
              {on && glow(x, 40, 11)}
              <Line points={[x - 13, 26, x + 13, 26, x + 9, 38, x - 9, 38]} closed fill={fixtureColor.base} stroke={COLOR_OUTLINE} strokeWidth={SITE_OUTLINE_WIDTH} />
            </Group>
          ))}
        </>
      ) : (
        <>
          {on && glow(124, 40, 12)}
          <Line points={[111, 26, 137, 26, 133, 38, 115, 38]} closed fill={fixtureColor.base} stroke={COLOR_OUTLINE} strokeWidth={SITE_OUTLINE_WIDTH} />
        </>
      )}
    </Group>
  );
}

export const LampPostDoubleSymbol: React.FC<SymbolProps> = ({ state }) => {
  const on = resolveSiteState(state, LAMP_POST_STATES, 'WYLACZONY') === 'ZALACZONY';
  return renderLampPost(2, on);
};

export const LampPostSingleSymbol: React.FC<SymbolProps> = ({ state }) => {
  const on = resolveSiteState(state, LAMP_POST_STATES, 'WYLACZONY') === 'ZALACZONY';
  return renderLampPost(1, on);
};
