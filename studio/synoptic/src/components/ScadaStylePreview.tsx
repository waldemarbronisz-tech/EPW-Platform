// Preview window for the new SCADA-style symbol set (src/symbols/scada/).
// Shows all nine symbols, in every state, on a canvas-colored background
// with a GRID_SIZE grid overlay and captions - separate from, and without
// touching, the existing editor canvas or Toolbox.

import React from 'react';
import { Group, Layer, Line, Rect, Stage, Text } from 'react-konva';
import { COLOR_CANVAS_BACKGROUND, COLOR_OUTLINE, COLOR_WHITE, GRID_SIZE, FONT_UI, FONT_SIZE_SMALL } from '../theme/ScadaTheme';
import { LoadSwitchSymbol, LOAD_SWITCH_STATES } from '../symbols/scada/LoadSwitchSymbol';
import { BusbarSymbol, BUSBAR_STATES } from '../symbols/scada/BusbarSymbol';
import { WireNodeSymbol } from '../symbols/scada/WireNodeSymbol';
import { LabelFrameSymbol } from '../symbols/scada/LabelFrameSymbol';
import { MotorSymbol, MOTOR_STATES } from '../symbols/scada/MotorSymbol';
import { PilotLampSymbol, PILOT_LAMP_STATES } from '../symbols/scada/PilotLampSymbol';
import { SocketSymbol, SOCKET_STATES } from '../symbols/scada/SocketSymbol';
import { IndicatorDiodeSymbol, INDICATOR_DIODE_STATES } from '../symbols/scada/IndicatorDiodeSymbol';
import type { IndicatorDiodeSize } from '../symbols/scada/IndicatorDiodeSymbol';
import { MeterSymbol } from '../symbols/scada/MeterSymbol';

export interface ScadaStylePreviewProps {
  onClose: () => void;
}

interface PreviewCell {
  title: string;
  render: () => React.ReactNode;
}

const COLUMNS = 5;
const CELL_WIDTH = 200;
const CELL_HEIGHT = 210;
const SYMBOL_TOP = 20;
const LABEL_Y = 190;

export const ScadaStylePreview: React.FC<ScadaStylePreviewProps> = ({ onClose }) => {
  const cells: PreviewCell[] = [];

  LOAD_SWITCH_STATES.forEach(state => {
    cells.push({ title: `Lacznik sterowany - ${state}`, render: () => <LoadSwitchSymbol state={state} /> });
  });

  BUSBAR_STATES.forEach(state => {
    cells.push({
      title: `Szyna zbiorcza - ${state}`,
      render: () => (
        <Group y={60}>
          <BusbarSymbol width={140} state={state} />
        </Group>
      )
    });
  });

  cells.push({ title: 'Wezel przewodu', render: () => <WireNodeSymbol /> });

  cells.push({
    title: 'Ramka opisowa',
    render: () => (
      <Group y={60}>
        <LabelFrameSymbol title="ZASILANIE" description="230V AC" />
      </Group>
    )
  });

  MOTOR_STATES.forEach(state => {
    cells.push({ title: `Silnik - ${state}`, render: () => <MotorSymbol state={state} /> });
  });

  PILOT_LAMP_STATES.forEach(state => {
    cells.push({ title: `Lampka - ${state}`, render: () => <PilotLampSymbol state={state} /> });
  });

  SOCKET_STATES.forEach(state => {
    cells.push({ title: `Gniazdo - ${state}`, render: () => <SocketSymbol state={state} /> });
  });

  (['small', 'large'] as IndicatorDiodeSize[]).forEach(size => {
    INDICATOR_DIODE_STATES.forEach(state => {
      cells.push({
        title: `Dioda (${size}) - ${state}`,
        render: () => (
          <Group y={60}>
            <IndicatorDiodeSymbol state={state} size={size} />
          </Group>
        )
      });
    });
  });

  cells.push({
    title: 'Miernik',
    render: () => (
      <Group y={30}>
        <MeterSymbol
          width={140}
          title="EPM01"
          rows={[
            { label: 'U L1', value: '230.4', unit: 'V' },
            { label: 'I L1', value: '12.7', unit: 'A' },
            { label: 'P', value: '2.93', unit: 'kW' }
          ]}
        />
      </Group>
    )
  });

  const rowCount = Math.ceil(cells.length / COLUMNS);
  const stageWidth = COLUMNS * CELL_WIDTH;
  const stageHeight = rowCount * CELL_HEIGHT;

  const gridLines: React.ReactNode[] = [];
  for (let x = 0; x <= stageWidth; x += GRID_SIZE) {
    gridLines.push(<Line key={`gx-${x}`} points={[x, 0, x, stageHeight]} stroke={COLOR_OUTLINE} strokeWidth={0.5} opacity={0.15} />);
  }
  for (let y = 0; y <= stageHeight; y += GRID_SIZE) {
    gridLines.push(<Line key={`gy-${y}`} points={[0, y, stageWidth, y]} stroke={COLOR_OUTLINE} strokeWidth={0.5} opacity={0.15} />);
  }

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', zIndex: 1000, display: 'flex', flexDirection: 'column' }}>
      <div style={{ background: '#2c2c2c', color: COLOR_WHITE, padding: '10px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0 }}>
        <span>SCADA Style Preview - 9 symboli, wszystkie stany</span>
        <button onClick={onClose}>Close</button>
      </div>
      <div style={{ flex: 1, overflow: 'auto', background: '#1a1a1a' }}>
        <Stage width={stageWidth} height={stageHeight}>
          <Layer>
            <Rect x={0} y={0} width={stageWidth} height={stageHeight} fill={COLOR_CANVAS_BACKGROUND} />
            {gridLines}
            {cells.map((cell, i) => {
              const col = i % COLUMNS;
              const row = Math.floor(i / COLUMNS);
              const cellX = col * CELL_WIDTH;
              const cellY = row * CELL_HEIGHT;
              const symbolX = cellX + (CELL_WIDTH - 150) / 2;

              return (
                <Group key={cell.title}>
                  <Group x={symbolX} y={cellY + SYMBOL_TOP}>
                    {cell.render()}
                  </Group>
                  <Text x={cellX} y={cellY + LABEL_Y} width={CELL_WIDTH} text={cell.title} fontSize={FONT_SIZE_SMALL} fontFamily={FONT_UI} align="center" fill={COLOR_OUTLINE} />
                </Group>
              );
            })}
          </Layer>
        </Stage>
      </div>
    </div>
  );
};
