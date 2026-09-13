// The row under the toolbar: the OPTIONS of the current work mode.
//
// The toolbar holds the tools (which Studio mirrors on its own toolbar);
// this row holds what does not fit on a row of icons - sliders, material
// lists, the text format bar - and stays visible inside Studio. It never
// disappears, so switching modes does not make the canvas jump: a mode
// with no options shows a one-line hint instead.
//
//   ROOMS        wall thickness / height / material | floor | illuminance, quantities
//   ANNOTATIONS  the Word-style format bar (FormatBar.tsx)
//   SYMBOLS, CONNECTIONS  a hint

import React, { useState } from 'react';
import { useStore } from '../store';
import { tr } from '../i18n/tr';
import { FormatBar } from './FormatBar';
import { RoomTakeoffDialog } from './RoomTakeoffDialog';
import {
  WALL_MIN_THICKNESS, WALL_MAX_THICKNESS, WALL_MIN_HEIGHT, WALL_MAX_HEIGHT,
} from '../elements/WallElement';
import { DEFAULT_FLOOR_MATERIAL, FLOOR_MATERIALS, WALL_MATERIALS } from '../theme/Materials';
import type { FloorMaterialId, WallMaterialId } from '../theme/Materials';

const RoomOptions: React.FC = () => {
  const wallDrawThickness = useStore(s => s.wallDrawThickness);
  const setWallDrawThickness = useStore(s => s.setWallDrawThickness);
  const wallDrawHeight = useStore(s => s.wallDrawHeight);
  const setWallDrawHeight = useStore(s => s.setWallDrawHeight);
  const wallDrawMaterial = useStore(s => s.wallDrawMaterial);
  const setWallDrawMaterial = useStore(s => s.setWallDrawMaterial);
  const floorMaterial = useStore(s => s.canvasConfig.floorMaterial);
  const setFloorMaterial = useStore(s => s.setFloorMaterial);
  const showIlluminance = useStore(s => s.showIlluminance);
  const setShowIlluminance = useStore(s => s.setShowIlluminance);
  const [showTakeoff, setShowTakeoff] = useState(false);

  return (
    <div className="format-bar mode-options-bar" data-mode-options="ROOMS">
      {showTakeoff && <RoomTakeoffDialog onClose={() => setShowTakeoff(false)} />}
      <div className="format-bar-group">
        <label title={tr('tool.wall_thickness')}>
          {tr('tool.wall_thickness')}: {wallDrawThickness}
          <input
            type="range"
            min={WALL_MIN_THICKNESS}
            max={WALL_MAX_THICKNESS}
            value={wallDrawThickness}
            onChange={e => setWallDrawThickness(Number(e.target.value))}
            style={{ width: 90, verticalAlign: 'middle' }}
          />
        </label>
        {/* A VIEW property, not a dimension: a real 2.5 m wall would bury
            the room in the drawing. The label says so. */}
        <label title={tr('tool.wall_height')}>
          {tr('tool.wall_height')}: {wallDrawHeight}
          <input
            type="range"
            min={WALL_MIN_HEIGHT}
            max={WALL_MAX_HEIGHT}
            value={wallDrawHeight}
            onChange={e => setWallDrawHeight(Number(e.target.value))}
            style={{ width: 90, verticalAlign: 'middle' }}
          />
        </label>
        <label>
          {tr('tool.wall_material')}{' '}
          <select value={wallDrawMaterial} onChange={e => setWallDrawMaterial(e.target.value as WallMaterialId)}>
            {Object.entries(WALL_MATERIALS).map(([id, m]) => (
              <option key={id} value={id}>{m.label}</option>
            ))}
          </select>
        </label>
      </div>
      <div className="format-bar-divider" />
      <div className="format-bar-group">
        <label>
          {tr('tool.floor')}{' '}
          <select
            value={floorMaterial ?? DEFAULT_FLOOR_MATERIAL}
            onChange={e => setFloorMaterial(e.target.value as FloorMaterialId)}
          >
            {Object.entries(FLOOR_MATERIALS).map(([id, m]) => (
              <option key={id} value={id}>{m.label}</option>
            ))}
          </select>
        </label>
      </div>
      <div className="format-bar-divider" />
      <div className="format-bar-group">
        <button
          className={`format-bar-wide${showIlluminance ? ' format-bar-pressed' : ''}`}
          aria-pressed={showIlluminance}
          title={tr('tool.illuminance_title')}
          onClick={() => setShowIlluminance(!showIlluminance)}
        >
          <span>{tr('tool.illuminance')}</span>
        </button>
        <button className="format-bar-wide" title={tr('tool.quantities_title')} onClick={() => setShowTakeoff(true)}>
          <span>&#931; {tr('tool.quantities')}</span>
        </button>
      </div>
    </div>
  );
};

export const ModeOptionsBar: React.FC = () => {
  const workMode = useStore(s => s.workMode);

  if (workMode === 'ANNOTATIONS') return <FormatBar />;
  if (workMode === 'ROOMS') return <RoomOptions />;
  return (
    <div className="format-bar mode-options-bar" data-mode-options={workMode}>
      <span className="mode-options-hint">{tr(`mode.hint.${workMode}`)}</span>
    </div>
  );
};
