// fix/room-move-and-edit: Properties for a selected ROOM - the walls
// selected together (a marquee round the room, or "Select the whole room"
// on one of its walls).
//
// Before this, selecting a room left Properties on "No object selected":
// the panel only knew a single wall. Here the room has what the user
// asked for - a name, the project location it belongs to, its position and
// size - plus what it measures. Moving it from here takes the symbols
// inside along, exactly as dragging it does (project/AreaMove.ts).

import React, { useEffect, useState } from 'react';
import { useStore } from '../store';
import { tr } from '../i18n/tr';
import { areaContents, roomSummary } from '../project/AreaMove';
import { GRID_SIZE } from '../theme/ScadaTheme';

const formatNumber = (value: number, digits = 2) => value.toFixed(digits).replace('.', ',');

/** A number box that applies on Enter or when left, like the size box of the format bar. */
const NumberField: React.FC<{ name: string; label: string; value: number; onCommit: (value: number) => void }> = ({ name, label, value, onCommit }) => {
  const [draft, setDraft] = useState<string | null>(null);
  useEffect(() => { setDraft(null); }, [value]);
  const commit = () => {
    if (draft === null) return;
    const parsed = Number(draft.replace(',', '.'));
    setDraft(null);
    if (Number.isFinite(parsed) && parsed !== value) onCommit(parsed);
  };
  return (
    <div className="property-row">
      <label>{label}</label>
      <input
        type="number"
        name={name}
        value={draft ?? String(Math.round(value))}
        onChange={e => setDraft(e.target.value)}
        onKeyDown={e => { if (e.key === 'Enter') commit(); e.stopPropagation(); }}
        onBlur={commit}
      />
    </div>
  );
};

export const RoomInspector: React.FC<{ wallIds: string[] }> = ({ wallIds }) => {
  const walls = useStore(s => s.walls);
  const rooms = useStore(s => s.rooms);
  const locations = useStore(s => s.locations);
  const summary = roomSummary(walls, wallIds, rooms);
  const box = summary.box;

  const setField = (key: 'name' | 'location', value: string) => {
    const s = useStore.getState();
    const roomId = s.assignRoomToWalls(wallIds);
    s.updateRoom(roomId, { [key]: value });
  };

  const moveTo = (x: number, y: number) => {
    if (!box) return;
    const s = useStore.getState();
    const contents = areaContents(s, wallIds);
    s.moveElementsBy({ ...contents, wallIds }, x - box.x, y - box.y);
  };

  const resizeTo = (width: number, height: number) => {
    if (!box) return;
    const s = useStore.getState();
    s.selectWalls(wallIds);
    s.scaleSelection(box, { x: box.x, y: box.y, width: Math.max(GRID_SIZE, width), height: Math.max(GRID_SIZE, height) }, GRID_SIZE);
    s.saveHistory();
  };

  const locationKnown = summary.location === null || summary.location === '' || locations.some(l => l.code === summary.location);

  return (
    <div className="property-inspector" data-inspector="room">
      <div className="inspector-header">{tr('room.title')}</div>
      <div className="inspector-content">
        <div className="property-group">
          <div className="property-group-title">{tr('room.title')}</div>
          <div className="property-row">
            <label>{tr('room.name')}</label>
            <input
              type="text"
              name="roomName"
              value={summary.name ?? ''}
              placeholder={summary.name === null ? tr('room.mixed') : ''}
              onChange={e => setField('name', e.target.value)}
              onBlur={() => useStore.getState().saveHistory()}
            />
          </div>
          <div className="property-row">
            <label>{tr('room.location')}</label>
            <select
              name="roomLocation"
              value={summary.location ?? ''}
              onChange={e => { setField('location', e.target.value); useStore.getState().saveHistory(); }}
            >
              <option value="">{tr('room.no_location')}</option>
              {!locationKnown && summary.location && <option value={summary.location}>{summary.location}</option>}
              {locations.map(l => (
                <option key={l.code} value={l.code}>{l.description ? `${l.code} - ${l.description}` : l.code}</option>
              ))}
            </select>
          </div>
        </div>

        {box && (
          <div className="property-group">
            <div className="property-group-title">{tr('room.layout')}</div>
            <NumberField name="roomX" label="X" value={box.x} onCommit={x => moveTo(x, box.y)} />
            <NumberField name="roomY" label="Y" value={box.y} onCommit={y => moveTo(box.x, y)} />
            <NumberField name="roomWidth" label={tr('room.width')} value={box.width} onCommit={w => resizeTo(w, box.height)} />
            <NumberField name="roomHeight" label={tr('room.height')} value={box.height} onCommit={h => resizeTo(box.width, h)} />
          </div>
        )}

        <div className="property-group">
          <div className="property-group-title">{tr('room.measures')}</div>
          <div className="property-row">
            <label>{tr('room.walls')}</label>
            <input type="text" value={String(summary.wallCount)} disabled />
          </div>
          <div className="property-row">
            <label>{tr('room.perimeter')}</label>
            <input type="text" name="roomPerimeter" value={`${formatNumber(summary.perimeterMetres)} m`} disabled />
          </div>
          <div className="property-row">
            <label>{tr('room.floor_area')}</label>
            <input
              type="text"
              name="roomFloorArea"
              value={summary.floorAreaSquareMetres === null ? tr('room.not_closed') : `${formatNumber(summary.floorAreaSquareMetres)} m2`}
              disabled
            />
          </div>
          <div className="property-row" style={{ opacity: 0.75 }}>{tr('room.move_hint')}</div>
        </div>
      </div>
    </div>
  );
};
