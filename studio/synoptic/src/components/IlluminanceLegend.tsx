// feat/room-lighting: the legend and the result box.
//
// A false-colour map without a scale is a pretty picture, so this is
// not optional decoration - it is the half that makes the map readable.
// The four figures beside it are the ones a lighting design is actually
// judged on, in the order a report states them: average, minimum,
// maximum, uniformity.
//
// Drawn as DOM over the canvas rather than inside the Konva stage: it
// must not pan, zoom, rotate or print with the drawing, and it must be
// selectable text.

import React, { useMemo } from 'react';
import { useStore } from '../store';
import { falseColour, roomIlluminanceStats } from '../project/Illuminance';
import { COLOR_OUTLINE, COLOR_PANEL, FONT_UI } from '../theme/ScadaTheme';

const boxStyle: React.CSSProperties = {
  position: 'absolute',
  right: 8,
  top: 8,
  background: COLOR_PANEL,
  border: `1px solid ${COLOR_OUTLINE}`,
  padding: 6,
  fontFamily: FONT_UI,
  // No explicit font-size: typography-proportions.test.ts keeps every
  // size in ScadaTheme, and this panel is not a reason to break that.
  pointerEvents: 'none',
  minWidth: 190,
  zIndex: 5,
};

const GRADIENT_STEPS = 40;

/** Rounded up to a readable scale top, so the legend's last number is 500 and not 487. */
function niceMax(value: number): number {
  if (value <= 0) return 1;
  const steps = [10, 20, 30, 50, 75, 100, 150, 200, 300, 500, 750, 1000, 1500, 2000, 3000, 5000];
  return steps.find(s => s >= value) ?? Math.ceil(value / 1000) * 1000;
}

export const IlluminanceLegend: React.FC = () => {
  const showIlluminance = useStore(s => s.showIlluminance);
  const walls = useStore(s => s.walls);
  const objects = useStore(s => s.objects);

  const rooms = useMemo(
    () => (showIlluminance ? roomIlluminanceStats(walls, objects) : []),
    [showIlluminance, walls, objects]
  );

  if (!showIlluminance) return null;

  const max = niceMax(Math.max(0, ...rooms.map(r => r.stats.max)));
  const gradient = `linear-gradient(to right, ${
    Array.from({ length: GRADIENT_STEPS }, (_, i) => {
      const [r, g, b] = falseColour(i / (GRADIENT_STEPS - 1));
      return `rgb(${r},${g},${b})`;
    }).join(', ')
  })`;

  const fmt = (value: number) => `${Math.round(value)} lx`;

  return (
    <div style={boxStyle}>
      <b>Illuminance</b>
      <div style={{ height: 12, background: gradient, border: `1px solid ${COLOR_OUTLINE}`, marginTop: 4 }} />
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <span>0</span>
        <span>{max} lx</span>
      </div>

      {rooms.length === 0 && <div style={{ marginTop: 4 }}>No closed room.</div>}

      {rooms.map(room => (
        <div key={room.index} style={{ marginTop: 6, borderTop: `1px solid ${COLOR_OUTLINE}`, paddingTop: 4 }}>
          {rooms.length > 1 && <div><b>Room {room.index + 1}</b></div>}
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span>E average</span><span>{fmt(room.stats.average)}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span>E min</span><span>{fmt(room.stats.min)}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span>E max</span><span>{fmt(room.stats.max)}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span>Uniformity</span><span>{room.stats.average > 0 ? room.stats.uniformity.toFixed(2).replace('.', ',') : '-'}</span>
          </div>
        </div>
      ))}

      {/* The limit, stated where the numbers are read rather than buried
          in a source comment - a direct-only figure read as a final one
          would under-light a room on paper and over-light it in the
          quote. */}
      <div style={{ marginTop: 6, opacity: 0.75 }}>
        Direct component only, no wall reflections.
      </div>
    </div>
  );
};
