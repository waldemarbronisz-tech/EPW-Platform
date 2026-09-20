// feat/workspace: "Oswietlenie" - the lighting result for this screen,
// as numbers rather than as a picture.
//
// The false-colour map (IlluminanceLayer) answers "where is it dark".
// This answers "does it pass", which is the question a design is
// actually signed off on: average, minimum, uniformity, compared against
// the maintained illuminance the room's use requires. PN-EN 12464-1 is
// the standard those figures come from, and its common values are
// offered here as a target to compare against - chosen by the user, not
// guessed from the drawing, because nothing on a floor plan says whether
// a room is an office or a corridor. Their lux figures are the
// standard's and do not translate; their names do.
//
// The limit is restated, not hidden: the calculation is direct-component
// only (no inter-reflection), so a real room will measure somewhat
// brighter. A figure read as final would under-light the room on paper
// and over-light it in the quote.

import React, { useMemo, useState } from 'react';
import { useStore } from '../store';
import { roomIlluminanceStats } from '../project/Illuminance';
import { tr } from '../i18n/tr';
import {
  COLOR_ALARM, COLOR_BEVEL_DARK, COLOR_OUTLINE, COLOR_PANEL, COLOR_RUN,
  COLOR_VALUE_FIELD, FONT_SIZE_SMALL, FONT_UI,
} from '../theme/ScadaTheme';

/**
 * Maintained illuminance for a few common uses, from PN-EN 12464-1's own
 * table. Offered as a comparison, never applied automatically - the
 * drawing does not know what the room is for.
 */
// The lux figures and the uniformities are the standard's, so they are
// data; only the room's NAME is language. The label is therefore looked
// up at render time rather than baked in here - this array is built
// once at module load, before a language has been chosen.
const TARGETS: { id: string; lux: number; uniformity: number }[] = [
  { id: 'none', lux: 0, uniformity: 0 },
  { id: 'corridor', lux: 100, uniformity: 0.4 },
  { id: 'store', lux: 150, uniformity: 0.4 },
  { id: 'workshop', lux: 200, uniformity: 0.4 },
  { id: 'office', lux: 500, uniformity: 0.6 },
  { id: 'precision', lux: 750, uniformity: 0.7 },
];

export const LightingPanel: React.FC = () => {
  const walls = useStore(s => s.walls);
  const objects = useStore(s => s.objects);
  const showIlluminance = useStore(s => s.showIlluminance);
  const setShowIlluminance = useStore(s => s.setShowIlluminance);

  const [targetId, setTargetId] = useState('none');
  const target = TARGETS.find(t => t.id === targetId) ?? TARGETS[0];

  const rooms = useMemo(() => roomIlluminanceStats(walls, objects), [walls, objects]);

  const fmt = (value: number) => `${Math.round(value)} lx`;
  const num = (value: number) => value.toFixed(2).replace('.', ',');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', fontFamily: FONT_UI, fontSize: FONT_SIZE_SMALL }}>
      <div
        style={{
          display: 'flex', alignItems: 'center', gap: 10, padding: '3px 8px',
          background: COLOR_PANEL, borderBottom: `1px solid ${COLOR_BEVEL_DARK}`,
        }}
      >
        <label style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <input
            type="checkbox"
            checked={showIlluminance}
            onChange={e => setShowIlluminance(e.target.checked)}
          />
          {tr('lighting.map_on_drawing')}
        </label>
        <label style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          {tr('lighting.required')}
          <select value={targetId} onChange={e => setTargetId(e.target.value)}>
            {TARGETS.map(t => <option key={t.id} value={t.id}>{tr(`lighting.target_${t.id}`)}</option>)}
          </select>
        </label>
        <span style={{ flex: 1 }} />
        <span style={{ opacity: 0.75 }}>{tr('lighting.direct_only')}</span>
      </div>

      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', background: COLOR_VALUE_FIELD }}>
        {rooms.length === 0 && (
          <div style={{ padding: 10, opacity: 0.8 }}>
            {tr('lighting.no_room')}
          </div>
        )}

        {rooms.map(room => {
          const { stats } = room;
          const lit = stats.max > 0;
          const passesLux = target.lux === 0 || stats.average >= target.lux;
          const passesUniformity = target.uniformity === 0 || stats.uniformity >= target.uniformity;
          const pass = passesLux && passesUniformity;

          return (
            <div key={room.index} style={{ padding: '4px 8px', borderBottom: `1px solid ${COLOR_PANEL}` }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <b>{tr('lighting.room', { index: room.index + 1 })}</b>
                {target.lux > 0 && lit && (
                  <span style={{ fontWeight: 'bold', color: pass ? COLOR_RUN : COLOR_ALARM }}>
                    {pass ? tr('lighting.pass') : tr('lighting.fail')}
                  </span>
                )}
                {!lit && <span style={{ opacity: 0.8 }}>{tr('lighting.unlit')}</span>}
              </div>

              {lit && (
                <div style={{ display: 'flex', gap: 18, marginTop: 2, color: COLOR_OUTLINE }}>
                  <span>{tr('lighting.e_avg')} <b style={{ color: passesLux || target.lux === 0 ? COLOR_OUTLINE : COLOR_ALARM }}>{fmt(stats.average)}</b></span>
                  <span>{tr('lighting.e_min')} <b>{fmt(stats.min)}</b></span>
                  <span>{tr('lighting.e_max')} <b>{fmt(stats.max)}</b></span>
                  <span>
                    Uo <b style={{ color: passesUniformity || target.uniformity === 0 ? COLOR_OUTLINE : COLOR_ALARM }}>
                      {stats.average > 0 ? num(stats.uniformity) : '-'}
                    </b>
                  </span>
                  {target.lux > 0 && (
                    <span style={{ opacity: 0.8 }}>
                      {tr('lighting.requirement', { lux: target.lux, uniformity: num(target.uniformity) })}
                    </span>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
