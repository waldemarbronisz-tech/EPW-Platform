import React from 'react';
import { useStore } from '../store';
import type { SynopticConnection } from '../store';
import {
  Undo, Redo, Copy, ClipboardPaste, Trash2,
  BringToFront, SendToBack, AlignLeft, AlignCenter, AlignRight,
  AlignVerticalSpaceAround, AlignHorizontalSpaceAround,
  Lock, Unlock, RotateCcw, RotateCw, PenLine, Zap, Droplet, Wind, Gauge, CircleDot,
  Square, Home, Power, SlidersHorizontal
} from 'lucide-react';
import { COLOR_ENERGIZED, COLOR_WATER, VENTILATION_ACTIVE, COLOR_WHITE, COLOR_RUN } from '../theme/ScadaTheme';
import { METER_DEFAULT_FONT_SIZE } from '../meter/MeterElement';
import { SIGNAL_PANEL_DEFAULT_FONT_SIZE } from '../elements/SignalPanelElement';
import { GROUP_COMMAND_DEFAULT_WIDTH } from '../elements/GroupCommandElement';
import { SETPOINT_DEFAULT_FONT_SIZE } from '../elements/SetpointElement';

// One icon/color pair per medium - reused by both the toolbar buttons
// below and nothing else, so this stays local rather than joining
// ScadaTheme.ts's own palette (which holds colors, not icon choices).
const MEDIUM_OPTIONS: { value: SynopticConnection['medium']; label: string; icon: React.FC<{ size?: number }>; color: string }[] = [
  { value: 'ELECTRICAL', label: 'Prad', icon: Zap, color: COLOR_ENERGIZED },
  { value: 'WATER', label: 'Woda', icon: Droplet, color: COLOR_WATER },
  { value: 'VENTILATION', label: 'Wentylacja', icon: Wind, color: VENTILATION_ACTIVE },
];

export const Toolbar: React.FC = () => {
  const {
    undo, redo, copySelected, paste, deleteObjects, selectedIds, selectedConnectionIds,
    bringToFront, sendToBack, alignSelected, distributeSelected,
    lockSelected, unlockSelected, rotateSelected,
    isDrawingConnection, setDrawingMode,
    drawingMedium, setDrawingMedium, drawingStyle, setDrawingStyle,
    wireRoutingMode, setWireRoutingMode,
    addMeter, selectedMeterIds, selectMeters,
    addSignalPanel, selectedSignalPanelIds, selectSignalPanels,
    selectedFrameIds, isDrawingFrame, drawingFrameVariant, setDrawingFrameMode,
    addGroupCommand, selectedGroupCommandIds, selectGroupCommands,
    addSetpointPanel, selectedSetpointPanelIds, selectSetpointPanels
  } = useStore();

  return (
    <div className="toolbar">
      <div className="toolbar-group">
        <button title="Undo" onClick={undo}><Undo size={16} /></button>
        <button title="Redo" onClick={redo}><Redo size={16} /></button>
      </div>

      <div className="toolbar-divider" />

      <div className="toolbar-group">
        <button title="Distribute Horizontally" onClick={() => distributeSelected('horizontal')}><AlignHorizontalSpaceAround size={16} /></button>
        <button title="Distribute Vertically" onClick={() => distributeSelected('vertical')}><AlignVerticalSpaceAround size={16} /></button>
      </div>

      <div className="toolbar-divider" />

      <div className="toolbar-group">
        <button title="Copy" onClick={copySelected}><Copy size={16} /></button>
        <button title="Paste" onClick={paste}><ClipboardPaste size={16} /></button>
        <button title="Delete" onClick={() => deleteObjects(selectedIds, selectedConnectionIds, selectedMeterIds, selectedSignalPanelIds, selectedFrameIds, selectedGroupCommandIds, selectedSetpointPanelIds)}><Trash2 size={16} /></button>
      </div>

      <div className="toolbar-divider" />

      {/* The meter element (feat/meter-element): not a symbol, so it has
          no Toolbox entry to drag from - this is how one gets placed.
          Dropped at a fixed default spot and auto-selected so it can be
          dragged into position right away, same as a pasted element. */}
      <div className="toolbar-group">
        <button
          title="Dodaj Miernik"
          onClick={() => {
            addMeter({ x: 160, y: 160, width: 200, fontSize: METER_DEFAULT_FONT_SIZE, rows: [] });
            const newest = useStore.getState().meters[useStore.getState().meters.length - 1];
            if (newest) selectMeters([newest.id], false);
          }}
        >
          <Gauge size={16} />
        </button>
      </div>

      {/* The signal panel element (commit 6): the same mechanism, the
          same reasoning for having a toolbar button at all. */}
      <div className="toolbar-group">
        <button
          title="Dodaj Panel Sygnalizacyjny"
          onClick={() => {
            addSignalPanel({ x: 160, y: 160, width: 160, fontSize: SIGNAL_PANEL_DEFAULT_FONT_SIZE, rows: [] });
            const newest = useStore.getState().signalPanels[useStore.getState().signalPanels.length - 1];
            if (newest) selectSignalPanels([newest.id], false);
          }}
        >
          <CircleDot size={16} />
        </button>
      </div>

      {/* The group command button (feat/control-elements commit 2): same
          mechanism, same reasoning for a toolbar button as the meter/
          signal panel above - one click to insert at a fixed spot, then
          drag into place, then configure label/command/members in
          Properties. */}
      <div className="toolbar-group">
        <button
          title="Dodaj Przycisk Grupowy"
          onClick={() => {
            addGroupCommand({ x: 160, y: 160, width: GROUP_COMMAND_DEFAULT_WIDTH, label: 'Nowy przycisk', command: 'CLOSE', deviceIds: [] });
            const newest = useStore.getState().groupCommands[useStore.getState().groupCommands.length - 1];
            if (newest) selectGroupCommands([newest.id], false);
          }}
        >
          <Power size={16} />
        </button>
      </div>

      {/* The setpoint panel element (feat/selector-symbol-setpoint-alarm):
          same mechanism, for MODULATED devices instead of MEASURED ones -
          see elements/SetpointElement.ts. */}
      <div className="toolbar-group">
        <button
          title="Dodaj Panel Nastaw"
          onClick={() => {
            addSetpointPanel({ x: 160, y: 160, width: 200, fontSize: SETPOINT_DEFAULT_FONT_SIZE, rows: [] });
            const newest = useStore.getState().setpointPanels[useStore.getState().setpointPanels.length - 1];
            if (newest) selectSetpointPanels([newest.id], false);
          }}
        >
          <SlidersHorizontal size={16} />
        </button>
      </div>

      <div className="toolbar-divider" />

      <div className="toolbar-group">
        <button
          title="Rysuj połączenie"
          onClick={() => setDrawingMode(!isDrawingConnection)}
          style={{ backgroundColor: isDrawingConnection ? '#3498db' : 'transparent' }}
        >
          <PenLine size={16} />
        </button>
      </div>

      <div className="toolbar-divider" />

      {/* The frame element (commit 3): drawn by dragging a rectangle on
          the canvas, like graphics.rectangle already is - two separate
          buttons for the two variants rather than one button plus a
          selector, matching this toolbar's own convention of dedicated
          single-purpose buttons.
          fix/handles-insert-mode-diodes commit 2: a plain click now
          arms the tool for ONE placement only - it returns to select
          mode right after a frame/building is drawn (Canvas.tsx's own
          handleMouseUp). Shift+click arms CONTINUOUS mode instead (the
          tool stays active, and stays highlighted below via the same
          isDrawingFrame-driven backgroundColor as before, for placing
          several in a row) - frameToolContinuous carries that choice
          from here through to Canvas.tsx's placement logic. Clicking
          the other button while one is already active still switches
          variant without needing to turn the tool off first. */}
      <div className="toolbar-group">
        <button
          title="Rysuj ramkę (Shift = tryb ciągły)"
          onClick={(e) => setDrawingFrameMode(!(isDrawingFrame && drawingFrameVariant === 'PLAIN'), 'PLAIN', e.shiftKey)}
          style={{ backgroundColor: isDrawingFrame && drawingFrameVariant === 'PLAIN' ? COLOR_RUN : 'transparent', color: isDrawingFrame && drawingFrameVariant === 'PLAIN' ? COLOR_WHITE : undefined }}
        >
          <Square size={16} />
        </button>
        <button
          title="Rysuj budynek (Shift = tryb ciągły)"
          onClick={(e) => setDrawingFrameMode(!(isDrawingFrame && drawingFrameVariant === 'BUILDING'), 'BUILDING', e.shiftKey)}
          style={{ backgroundColor: isDrawingFrame && drawingFrameVariant === 'BUILDING' ? COLOR_RUN : 'transparent', color: isDrawingFrame && drawingFrameVariant === 'BUILDING' ? COLOR_WHITE : undefined }}
        >
          <Home size={16} />
        </button>
      </div>

      {/* Medium selector (part C): which of the three media a NEWLY
          drawn wire gets, chosen up front instead of after the fact in
          Properties - applies to every wire drawn until changed again.
          Keyboard shortcuts 1/2/3 do the same (Canvas.tsx). */}
      <div className="toolbar-group">
        {MEDIUM_OPTIONS.map(({ value, label, icon: Icon, color }) => (
          <button
            key={value}
            title={label}
            onClick={() => setDrawingMedium(value)}
            style={{
              backgroundColor: drawingMedium === value ? color : 'transparent',
              color: drawingMedium === value ? COLOR_WHITE : undefined
            }}
          >
            <Icon size={16} />
          </button>
        ))}
      </div>

      {/* Style selector for newly drawn wires: NORMAL or BUS (a thicker
          busbar/manifold, touchable anywhere along its length). */}
      <div className="toolbar-group">
        <button
          title="Normal"
          onClick={() => setDrawingStyle('NORMAL')}
          style={{ backgroundColor: drawingStyle === 'NORMAL' ? COLOR_RUN : 'transparent', color: drawingStyle === 'NORMAL' ? COLOR_WHITE : undefined }}
        >
          N
        </button>
        <button
          title="Bus (szyna / kolektor)"
          onClick={() => setDrawingStyle('BUS')}
          style={{ backgroundColor: drawingStyle === 'BUS' ? COLOR_RUN : 'transparent', color: drawingStyle === 'BUS' ? COLOR_WHITE : undefined }}
        >
          B
        </button>
      </div>

      {/* feat/wire-routing-around-obstacles commit 3, point (a): PROSTO
          (every bend placed by hand, today's existing behavior) or
          OMIJAJ (a new wire's route is computed automatically around
          obstacles) - OMIJAJ by default. Session-only (wireRoutingMode
          lives in toolsSlice.ts, never in the saved project file), same
          convention as the medium/style selectors right above. */}
      <div className="toolbar-group">
        <button
          title="Prosto (uzytkownik sam stawia zalamania)"
          onClick={() => setWireRoutingMode('STRAIGHT')}
          style={{ backgroundColor: wireRoutingMode === 'STRAIGHT' ? COLOR_RUN : 'transparent', color: wireRoutingMode === 'STRAIGHT' ? COLOR_WHITE : undefined }}
        >
          P
        </button>
        <button
          title="Omijaj (trasa liczona automatycznie wokol przeszkod)"
          onClick={() => setWireRoutingMode('AVOID')}
          style={{ backgroundColor: wireRoutingMode === 'AVOID' ? COLOR_RUN : 'transparent', color: wireRoutingMode === 'AVOID' ? COLOR_WHITE : undefined }}
        >
          O
        </button>
      </div>

      <div className="toolbar-divider" />

      <div className="toolbar-group">
        <button title="Bring to Front" onClick={bringToFront}><BringToFront size={16} /></button>
        <button title="Send to Back" onClick={sendToBack}><SendToBack size={16} /></button>
      </div>

      <div className="toolbar-divider" />

      <div className="toolbar-group">
        <button title="Align Left" onClick={() => alignSelected('left')}><AlignLeft size={16} /></button>
        <button title="Align Center" onClick={() => alignSelected('center')}><AlignCenter size={16} /></button>
        <button title="Align Right" onClick={() => alignSelected('right')}><AlignRight size={16} /></button>
      </div>

      <div className="toolbar-group">
        <button title="Align Middle" onClick={() => alignSelected('middle')}><AlignVerticalSpaceAround size={16} /></button>
      </div>

      <div className="toolbar-divider" />

      <div className="toolbar-group">
        <button title="Lock" onClick={lockSelected}><Lock size={16} /></button>
        <button title="Unlock" onClick={unlockSelected}><Unlock size={16} /></button>
      </div>

      <div className="toolbar-divider" />

      <div className="toolbar-group">
        <button title="Rotate Left" onClick={() => rotateSelected('ccw')}><RotateCcw size={16} /></button>
        <button title="Rotate Right" onClick={() => rotateSelected('cw')}><RotateCw size={16} /></button>
      </div>
    </div>
  );
};
