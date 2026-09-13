// feat/toolbar-grouping: the SCADA department's own tools, in the Object
// Library.
//
// The top toolbar used to carry every way of putting something on the
// screen - meters, signal panels, group commands, setpoint panels, the
// wire tool with its medium / style / routing options, frames - next to
// copy, paste and undo. That made it a long row of look-alike icons where
// the basic commands were hard to find. Inserting things now lives where
// everything else is inserted from: the library, under SCADA, the same
// way the BUILDING department carries its wall and room tools. The top
// bar keeps the basics.
//
// The wire tool's options (medium, style, routing) are shown only while
// the tool is armed - they describe the NEXT wire, so they are noise the
// rest of the time.

import React from 'react';
import { useStore } from '../store';
import type { SynopticConnection } from '../store';
import { METER_DEFAULT_FONT_SIZE } from '../meter/MeterElement';
import { SIGNAL_PANEL_DEFAULT_FONT_SIZE } from '../elements/SignalPanelElement';
import { GROUP_COMMAND_DEFAULT_WIDTH } from '../elements/GroupCommandElement';
import { SETPOINT_DEFAULT_FONT_SIZE } from '../elements/SetpointElement';
import { ElectricalPixelIcon, WaterPixelIcon } from './icons/MediumPixelIcons';
import { insertTextBox } from './insertTextBox';
import { COLOR_RUN, COLOR_WHITE } from '../theme/ScadaTheme';

const MEDIA: { value: SynopticConnection['medium']; label: string; icon?: React.FC<{ size?: number }> }[] = [
  { value: 'ELECTRICAL', label: 'Electrical', icon: ElectricalPixelIcon },
  { value: 'WATER', label: 'Water', icon: WaterPixelIcon },
  { value: 'VENTILATION', label: 'Ventilation' },
];

const armedStyle = (on: boolean): React.CSSProperties => ({
  cursor: 'pointer',
  fontWeight: on ? 'bold' : undefined,
  background: on ? COLOR_RUN : undefined,
  color: on ? COLOR_WHITE : undefined,
});

const optionStyle = (on: boolean): React.CSSProperties => ({
  display: 'inline-flex',
  alignItems: 'center',
  gap: 4,
  padding: '1px 6px',
  fontWeight: on ? 'bold' : 'normal',
  background: on ? COLOR_RUN : undefined,
  color: on ? COLOR_WHITE : undefined,
});

export const ScadaTools: React.FC = () => {
  const {
    addMeter, selectMeters, addSignalPanel, selectSignalPanels,
    addGroupCommand, selectGroupCommands, addSetpointPanel, selectSetpointPanels,
    isDrawingConnection, setDrawingMode,
    drawingMedium, setDrawingMedium, drawingStyle, setDrawingStyle,
    wireRoutingMode, setWireRoutingMode,
    isDrawingFrame, drawingFrameVariant, setDrawingFrameMode,
  } = useStore();

  const insert = (label: string, title: string, action: () => void) => (
    <div className="library-item" onClick={action} style={{ cursor: 'pointer' }} title={title}>
      + {label}
    </div>
  );

  return (
    <>
      {insert('Text box', 'Insert a text box and start typing', insertTextBox)}
      {insert('Meter', 'Add Meter', () => {
        addMeter({ x: 160, y: 160, width: 200, fontSize: METER_DEFAULT_FONT_SIZE, rows: [] });
        const newest = useStore.getState().meters[useStore.getState().meters.length - 1];
        if (newest) selectMeters([newest.id], false);
      })}
      {insert('Signal panel', 'Add Signal Panel', () => {
        addSignalPanel({ x: 160, y: 160, width: 160, fontSize: SIGNAL_PANEL_DEFAULT_FONT_SIZE, rows: [] });
        const newest = useStore.getState().signalPanels[useStore.getState().signalPanels.length - 1];
        if (newest) selectSignalPanels([newest.id], false);
      })}
      {insert('Group command button', 'Add Group Command Button', () => {
        addGroupCommand({ x: 160, y: 160, width: GROUP_COMMAND_DEFAULT_WIDTH, label: 'New button', command: 'CLOSE', deviceIds: [] });
        const newest = useStore.getState().groupCommands[useStore.getState().groupCommands.length - 1];
        if (newest) selectGroupCommands([newest.id], false);
      })}
      {insert('Setpoint panel', 'Add Setpoint Panel', () => {
        addSetpointPanel({ x: 160, y: 160, width: 200, fontSize: SETPOINT_DEFAULT_FONT_SIZE, rows: [] });
        const newest = useStore.getState().setpointPanels[useStore.getState().setpointPanels.length - 1];
        if (newest) selectSetpointPanels([newest.id], false);
      })}

      <div
        className="library-item"
        onClick={() => setDrawingMode(!isDrawingConnection)}
        style={armedStyle(isDrawingConnection)}
        title="Draw Wire"
      >
        {isDrawingConnection ? '■' : '□'} Draw wire
      </div>

      {isDrawingConnection && (
        <div style={{ padding: '2px 8px 6px 20px', display: 'grid', gap: 3 }}>
          <div style={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
            {MEDIA.map(({ value, label, icon: Icon }) => (
              <span
                key={value}
                role="button"
                title={label}
                style={{ ...optionStyle(drawingMedium === value), cursor: 'pointer' }}
                onClick={() => setDrawingMedium(value)}
              >
                {Icon && <Icon size={14} />}{label}
              </span>
            ))}
          </div>
          <div style={{ display: 'flex', gap: 3 }}>
            <span role="button" title="Normal" style={{ ...optionStyle(drawingStyle === 'NORMAL'), cursor: 'pointer' }} onClick={() => setDrawingStyle('NORMAL')}>Normal</span>
            <span role="button" title="Bus (busbar / manifold)" style={{ ...optionStyle(drawingStyle === 'BUS'), cursor: 'pointer' }} onClick={() => setDrawingStyle('BUS')}>Bus</span>
          </div>
          <div style={{ display: 'flex', gap: 3 }}>
            <span role="button" title="Direct (the user places every bend by hand)" style={{ ...optionStyle(wireRoutingMode === 'STRAIGHT'), cursor: 'pointer' }} onClick={() => setWireRoutingMode('STRAIGHT')}>Direct</span>
            <span role="button" title="Avoid (route computed automatically around obstacles)" style={{ ...optionStyle(wireRoutingMode === 'AVOID'), cursor: 'pointer' }} onClick={() => setWireRoutingMode('AVOID')}>Avoid</span>
          </div>
        </div>
      )}

      <div
        className="library-item"
        onClick={e => setDrawingFrameMode(!(isDrawingFrame && drawingFrameVariant === 'PLAIN'), 'PLAIN', e.shiftKey)}
        style={armedStyle(isDrawingFrame && drawingFrameVariant === 'PLAIN')}
        title="Draw Frame (Shift = continuous mode)"
      >
        {isDrawingFrame && drawingFrameVariant === 'PLAIN' ? '■' : '□'} Draw frame
      </div>
      <div
        className="library-item"
        onClick={e => setDrawingFrameMode(!(isDrawingFrame && drawingFrameVariant === 'BUILDING'), 'BUILDING', e.shiftKey)}
        style={armedStyle(isDrawingFrame && drawingFrameVariant === 'BUILDING')}
        title="Draw Building (Shift = continuous mode)"
      >
        {isDrawingFrame && drawingFrameVariant === 'BUILDING' ? '■' : '□'} Draw building outline
      </div>
    </>
  );
};
