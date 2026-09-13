// feat/workspace: "Zestawienie" - the quantities this screen adds up to,
// at a glance.
//
// The full schedule already exists as a dialog (RoomTakeoffDialog) with
// every row in it. This is the other half of the same need: the four or
// five numbers someone keeps looking back at while drawing - how much
// wall, how much floor, how many fixtures, how many circuits still
// unwired - without a modal covering the plan they are drawing.
//
// The full schedule is one button away, because the moment those numbers
// are being quoted rather than glanced at, the detail matters.

import React, { useMemo, useState } from 'react';
import { useStore } from '../store';
import { buildRoomTakeoff } from '../project/RoomTakeoff';
import { RoomTakeoffDialog } from './RoomTakeoffDialog';
import { formatLength, pxToCm } from '../theme/Scale';
import {
  COLOR_ALARM, COLOR_BEVEL_DARK, COLOR_OUTLINE, COLOR_PANEL, COLOR_RUN,
  COLOR_VALUE_FIELD, FONT_SIZE_SMALL, FONT_SIZE_TITLE, FONT_UI,
} from '../theme/ScadaTheme';

/** Square pixels to square metres. The plan works in pixels (Scale.ts: 1 m = 80 px), so an area is that factor squared. */
function areaInSquareMetres(areaPx: number): number {
  const metresPerPixel = pxToCm(1) / 100;
  return areaPx * metresPerPixel * metresPerPixel;
}

const cardStyle: React.CSSProperties = {
  background: COLOR_VALUE_FIELD,
  border: `1px solid ${COLOR_BEVEL_DARK}`,
  padding: '4px 10px',
  minWidth: 110,
};

export const TakeoffPanel: React.FC = () => {
  const walls = useStore(s => s.walls);
  const objects = useStore(s => s.objects);
  const circuits = useStore(s => s.circuits);
  const devices = useStore(s => s.devices);
  const floorMaterial = useStore(s => s.canvasConfig.floorMaterial);
  const [showFull, setShowFull] = useState(false);

  const takeoff = useMemo(
    () => buildRoomTakeoff(walls, objects, circuits, devices, floorMaterial),
    [walls, objects, circuits, devices, floorMaterial]
  );

  const { totals } = takeoff;

  const cards: { label: string; value: string; alarm?: boolean }[] = [
    { label: 'Wall length', value: formatLength(totals.wallLength) },
    { label: 'Wall area', value: `${areaInSquareMetres(totals.wallArea).toFixed(1).replace('.', ',')} m2` },
    { label: 'Floor area', value: `${areaInSquareMetres(totals.floorArea).toFixed(1).replace('.', ',')} m2` },
    { label: 'Devices', value: `${totals.fixtures} pcs` },
    { label: 'Circuits', value: `${takeoff.circuits.length} pcs` },
    {
      label: 'Without device',
      value: `${totals.unwiredCircuits} pcs`,
      alarm: totals.unwiredCircuits > 0,
    },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', fontFamily: FONT_UI, fontSize: FONT_SIZE_SMALL }}>
      <div
        style={{
          display: 'flex', alignItems: 'center', gap: 10, padding: '3px 8px',
          background: COLOR_PANEL, borderBottom: `1px solid ${COLOR_BEVEL_DARK}`,
        }}
      >
        <b>Quantities for this screen</b>
        <span style={{ flex: 1 }} />
        <button onClick={() => setShowFull(true)} style={{ padding: '0 10px' }} title="Full schedule with every item">
          Full schedule...
        </button>
      </div>

      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', padding: 8, background: COLOR_PANEL }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {cards.map(card => (
            <div key={card.label} style={cardStyle}>
              <div style={{ opacity: 0.8 }}>{card.label}</div>
              <div
                style={{
                  fontSize: FONT_SIZE_TITLE,
                  fontWeight: 'bold',
                  color: card.alarm ? COLOR_ALARM : COLOR_OUTLINE,
                }}
              >
                {card.value}
              </div>
            </div>
          ))}
        </div>

        {totals.unwiredCircuits === 0 && takeoff.circuits.length > 0 && (
          <div style={{ marginTop: 8, color: COLOR_RUN }}>
            Every circuit has a device assigned.
          </div>
        )}
      </div>

      {showFull && <RoomTakeoffDialog onClose={() => setShowFull(false)} />}
    </div>
  );
};
