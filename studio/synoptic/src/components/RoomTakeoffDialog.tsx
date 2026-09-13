// feat/room-plan: the schedule window - what the drawn room contains.
//
// Every figure comes from project/RoomTakeoff.ts, which derives all of
// it from the drawing itself. Nothing here is entered, stored or
// cached: the dialog reads the current store each time it opens, so it
// cannot show a stale quantity for a wall that has since been moved.
//
// Same modal convention as the other dialogs in this editor (backdrop
// as a SIBLING of the box, not its parent - see DeviceListDialog).

import React, { useMemo, useState } from 'react';
import { useStore } from '../store';
import { buildRoomTakeoff, takeoffToText } from '../project/RoomTakeoff';
import { COLOR_ALARM, COLOR_PANEL, COLOR_OUTLINE, FONT_SIZE_BASE, FONT_UI } from '../theme/ScadaTheme';

export interface RoomTakeoffDialogProps {
  onClose: () => void;
}

const backdropStyle: React.CSSProperties = {
  position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)', zIndex: 900,
};

const dialogStyle: React.CSSProperties = {
  position: 'fixed', top: '8%', left: '50%', transform: 'translateX(-50%)',
  width: 640, maxHeight: '80vh', overflow: 'auto',
  background: COLOR_PANEL, border: `2px solid ${COLOR_OUTLINE}`,
  fontFamily: FONT_UI, fontSize: FONT_SIZE_BASE, zIndex: 901,
};

const headerStyle: React.CSSProperties = {
  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
  background: '#000080', color: '#FFFFFF', padding: '2px 6px', fontWeight: 'bold',
};

const sectionStyle: React.CSSProperties = { padding: '6px 10px' };
const tableStyle: React.CSSProperties = { width: '100%', borderCollapse: 'collapse' };
const thStyle: React.CSSProperties = { textAlign: 'left', borderBottom: `1px solid ${COLOR_OUTLINE}` };
const numStyle: React.CSSProperties = { textAlign: 'right' };

/** Polish decimal comma - this is a document a Polish electrician reads, not a JSON payload. */
const n = (value: number, digits = 2) => value.toFixed(digits).replace('.', ',');

export const RoomTakeoffDialog: React.FC<RoomTakeoffDialogProps> = ({ onClose }) => {
  const walls = useStore(s => s.walls);
  const objects = useStore(s => s.objects);
  const circuits = useStore(s => s.circuits);
  const devices = useStore(s => s.devices);
  const floorMaterial = useStore(s => s.canvasConfig.floorMaterial);
  const [copied, setCopied] = useState(false);

  const takeoff = useMemo(
    () => buildRoomTakeoff(walls, objects, circuits, devices, floorMaterial),
    [walls, objects, circuits, devices, floorMaterial]
  );

  const copy = () => {
    // Best-effort: a denied clipboard permission must not throw an
    // unhandled rejection across the editor.
    navigator.clipboard?.writeText(takeoffToText(takeoff))
      .then(() => setCopied(true))
      .catch(() => setCopied(false));
  };

  const empty = takeoff.walls.length === 0 && takeoff.fixtures.length === 0;

  return (
    <>
      <div style={backdropStyle} onClick={onClose} />
      <div style={dialogStyle} onClick={e => e.stopPropagation()}>
        <div style={headerStyle}>
          <span>Quantities</span>
          <button onClick={onClose} title="Close">x</button>
        </div>

        {empty ? (
          <div style={sectionStyle}>Nothing has been drawn yet.</div>
        ) : (
          <>
            <div style={sectionStyle}>
              <b>Walls</b>
              <table style={tableStyle}>
                <thead>
                  <tr>
                    <th style={thStyle}>Material</th>
                    <th style={{ ...thStyle, ...numStyle }}>Segments</th>
                    <th style={{ ...thStyle, ...numStyle }}>Length [m]</th>
                    <th style={{ ...thStyle, ...numStyle }}>Height [m]</th>
                    <th style={{ ...thStyle, ...numStyle }}>Face [m2]</th>
                  </tr>
                </thead>
                <tbody>
                  {takeoff.walls.map(row => (
                    <tr key={row.material}>
                      <td>{row.materialLabel}</td>
                      <td style={numStyle}>{row.count}</td>
                      <td style={numStyle}>{n(row.length)}</td>
                      <td style={numStyle}>{row.height === null ? 'mixed' : n(row.height)}</td>
                      <td style={numStyle}>{n(row.area)}</td>
                    </tr>
                  ))}
                  <tr>
                    <td><b>Total</b></td>
                    <td style={numStyle} />
                    <td style={numStyle}><b>{n(takeoff.totals.wallLength)}</b></td>
                    <td style={numStyle} />
                    <td style={numStyle}><b>{n(takeoff.totals.wallArea)}</b></td>
                  </tr>
                </tbody>
              </table>
            </div>

            {takeoff.floors.length > 0 && (
              <div style={sectionStyle}>
                <b>Floor</b>
                <table style={tableStyle}>
                  <thead>
                    <tr>
                      <th style={thStyle}>Material</th>
                      <th style={{ ...thStyle, ...numStyle }}>Rooms</th>
                      <th style={{ ...thStyle, ...numStyle }}>Area [m2]</th>
                    </tr>
                  </thead>
                  <tbody>
                    {takeoff.floors.map(row => (
                      <tr key={row.materialLabel}>
                        <td>{row.materialLabel}</td>
                        <td style={numStyle}>{row.rooms}</td>
                        <td style={numStyle}>{n(row.area)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {takeoff.fixtures.length > 0 && (
              <div style={sectionStyle}>
                <b>Items</b>
                <table style={tableStyle}>
                  <thead>
                    <tr>
                      <th style={thStyle}>Item</th>
                      <th style={{ ...thStyle, ...numStyle }}>Qty</th>
                    </tr>
                  </thead>
                  <tbody>
                    {takeoff.fixtures.map(row => (
                      <tr key={row.type}>
                        <td>{row.label}</td>
                        <td style={numStyle}>{row.count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {takeoff.lighting.length > 0 && (
              <div style={sectionStyle}>
                <b>Lighting</b>
                <table style={tableStyle}>
                  <thead>
                    <tr>
                      <th style={thStyle}>Room</th>
                      <th style={{ ...thStyle, ...numStyle }}>E avg [lx]</th>
                      <th style={{ ...thStyle, ...numStyle }}>E min [lx]</th>
                      <th style={{ ...thStyle, ...numStyle }}>E max [lx]</th>
                      <th style={{ ...thStyle, ...numStyle }}>Unif.</th>
                      <th style={{ ...thStyle, ...numStyle }}>lm/m2</th>
                    </tr>
                  </thead>
                  <tbody>
                    {takeoff.lighting.map(row => (
                      <tr key={row.room}>
                        <td>{row.room}</td>
                        <td style={numStyle}>{Math.round(row.average)}</td>
                        {/* The minimum is the figure a lighting design
                            usually fails on, and uniformity below 0,40
                            is the usual threshold for a working
                            interior - both called out rather than left
                            for the reader to spot. */}
                        <td style={numStyle}>{Math.round(row.min)}</td>
                        <td style={numStyle}>{Math.round(row.max)}</td>
                        <td style={row.uniformity < 0.4 ? { ...numStyle, color: COLOR_ALARM } : numStyle}>
                          {n(row.uniformity)}
                        </td>
                        <td style={numStyle}>{Math.round(row.fluxDensity)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <div style={{ marginTop: 4, opacity: 0.75 }}>
                  Direct component only, no wall reflections - real values will be higher.
                </div>
              </div>
            )}

            {takeoff.circuits.length > 0 && (
              <div style={sectionStyle}>
                <b>Circuits</b>
                <table style={tableStyle}>
                  <thead>
                    <tr>
                      <th style={thStyle}>Circuit</th>
                      <th style={{ ...thStyle, ...numStyle }}>Loads</th>
                      <th style={thStyle}>Control</th>
                      <th style={thStyle}>Feedback</th>
                    </tr>
                  </thead>
                  <tbody>
                    {takeoff.circuits.map(row => (
                      <tr key={row.name}>
                        <td>{row.name}</td>
                        <td style={numStyle}>{row.fixtures}</td>
                        {/* An unwired circuit is called out in the alarm
                            colour: it is the one thing in this window
                            that is actionable - a circuit nothing can
                            switch is an unfinished installation, not a
                            quantity. */}
                        <td style={row.wired ? undefined : { color: COLOR_ALARM }}>{row.binding}</td>
                        {/* NOT flagged as a problem when absent: a
                            lighting circuit on a plain DO has nothing to
                            confirm it, and that is the normal case. */}
                        <td style={{ opacity: row.assumed ? 0.75 : 1 }}>{row.feedback}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {takeoff.totals.unwiredCircuits > 0 && (
                  <div style={{ color: COLOR_ALARM, marginTop: 4 }}>
                    Circuits without a bound device: {takeoff.totals.unwiredCircuits}
                  </div>
                )}
              </div>
            )}
          </>
        )}

        <div style={{ ...sectionStyle, display: 'flex', gap: 8, alignItems: 'center' }}>
          <button onClick={copy}>Copy to clipboard</button>
          {copied && <span>copied</span>}
          <span style={{ flex: 1 }} />
          <button onClick={onClose}>Close</button>
        </div>
      </div>
    </>
  );
};
