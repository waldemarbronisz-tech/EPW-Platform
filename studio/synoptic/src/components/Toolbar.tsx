import React from 'react';
import { useStore } from '../store';
import { StudioIcon } from './icons/StudioIcon';
import type { SynopticConnection } from '../store';
import { COLOR_ENERGIZED, COLOR_WATER, VENTILATION_ACTIVE, COLOR_WHITE, COLOR_RUN } from '../theme/ScadaTheme';

// Wire drawing stays on the toolbar: it is used constantly while drawing,
// and Studio's own toolbar mirrors these buttons. Inserting meters and
// panels lives in the library's SCADA department (ScadaTools.tsx).
const MEDIUM_OPTIONS: { value: SynopticConnection['medium']; label: string; icon: string; color: string }[] = [
  { value: 'ELECTRICAL', label: 'Electrical', icon: 'medium_electrical', color: COLOR_ENERGIZED },
  { value: 'WATER', label: 'Water', icon: 'medium_water', color: COLOR_WATER },
  { value: 'VENTILATION', label: 'Ventilation', icon: 'medium_ventilation', color: VENTILATION_ACTIVE },
];

export const Toolbar: React.FC = () => {
  const {
    undo, redo, copySelected, paste, deleteObjects, selectedIds, selectedConnectionIds,
    bringToFront, sendToBack,
    lockSelected, unlockSelected, rotateSelected,
    selectedMeterIds, selectedSignalPanelIds, selectedFrameIds,
    selectedGroupCommandIds, selectedSetpointPanelIds,
    previewMode, setPreviewMode,
    selectedWallIds,
    isDrawingConnection, setDrawingMode,
    drawingMedium, setDrawingMedium, drawingStyle, setDrawingStyle,
    wireRoutingMode, setWireRoutingMode,
    isDrawingFrame, drawingFrameVariant, setDrawingFrameMode
  } = useStore();

  return (
    <div className="toolbar">
      <div className="toolbar-group">
        <button title="Undo" onClick={undo}><StudioIcon name="undo" /></button>
        <button title="Redo" onClick={redo}><StudioIcon name="redo" /></button>
      </div>

      <div className="toolbar-divider" />

      <div className="toolbar-group">
        <button title="Copy" onClick={copySelected}><StudioIcon name="copy" /></button>
        <button title="Paste" onClick={paste}><StudioIcon name="paste" /></button>
        <button title="Delete" onClick={() => deleteObjects(selectedIds, selectedConnectionIds, selectedMeterIds, selectedSignalPanelIds, selectedFrameIds, selectedGroupCommandIds, selectedSetpointPanelIds, selectedWallIds)}><StudioIcon name="delete" /></button>
      </div>

      <div className="toolbar-divider" />

      {/* feat/toolbar-grouping: inserting elements, drawing wires and
          frames and the wire options moved to the Object Library's
          SCADA department (ScadaTools.tsx); text formatting has its
          own bar (FormatBar.tsx). This bar keeps the basics. */}
      {/* feat/room-plan: Podglad. A MODE, not a tool - it changes what a
          click MEANS everywhere on the canvas (operate the circuit
          under the cursor instead of selecting the element), so it
          belongs in the toolbar beside the other global states, not in
          the BUDYNEK department of the Object Library where the
          building ELEMENTS live. Arming it disarms every drawing tool
          (toolsSlice.setPreviewMode) - being ready to draw while clicks
          operate circuits is a contradiction, not a combination. */}
      <div className="toolbar-group">
        <button
          title="Preview - a click switches a circuit on or off instead of selecting the element"
          onClick={() => setPreviewMode(!previewMode)}
          style={{ backgroundColor: previewMode ? COLOR_RUN : 'transparent', color: previewMode ? COLOR_WHITE : undefined }}
        >
          <StudioIcon name="preview_mode" />
        </button>
      </div>

      <div className="toolbar-divider" />

      <div className="toolbar-group">
        <button
          title="Draw Wire"
          onClick={() => setDrawingMode(!isDrawingConnection)}
          style={{ backgroundColor: isDrawingConnection ? COLOR_RUN : 'transparent', color: isDrawingConnection ? COLOR_WHITE : undefined }}
        >
          <StudioIcon name="draw_wire" />
        </button>
        <button
          title="Draw Frame (Shift = continuous mode)"
          onClick={(e) => setDrawingFrameMode(!(isDrawingFrame && drawingFrameVariant === 'PLAIN'), 'PLAIN', e.shiftKey)}
          style={{ backgroundColor: isDrawingFrame && drawingFrameVariant === 'PLAIN' ? COLOR_RUN : 'transparent', color: isDrawingFrame && drawingFrameVariant === 'PLAIN' ? COLOR_WHITE : undefined }}
        >
          <StudioIcon name="draw_frame" />
        </button>
        <button
          title="Draw Building (Shift = continuous mode)"
          onClick={(e) => setDrawingFrameMode(!(isDrawingFrame && drawingFrameVariant === 'BUILDING'), 'BUILDING', e.shiftKey)}
          style={{ backgroundColor: isDrawingFrame && drawingFrameVariant === 'BUILDING' ? COLOR_RUN : 'transparent', color: isDrawingFrame && drawingFrameVariant === 'BUILDING' ? COLOR_WHITE : undefined }}
        >
          <StudioIcon name="draw_building" />
        </button>
      </div>

      <div className="toolbar-group">
        {MEDIUM_OPTIONS.map(({ value, label, icon, color }) => (
          <button
            key={value}
            title={label}
            onClick={() => setDrawingMedium(value)}
            style={{ backgroundColor: drawingMedium === value ? color : 'transparent', color: drawingMedium === value ? COLOR_WHITE : undefined }}
          >
            <StudioIcon name={icon} />
          </button>
        ))}
      </div>

      <div className="toolbar-group">
        <button title="Normal" onClick={() => setDrawingStyle('NORMAL')} style={{ backgroundColor: drawingStyle === 'NORMAL' ? COLOR_RUN : 'transparent', color: drawingStyle === 'NORMAL' ? COLOR_WHITE : undefined }}><StudioIcon name="wire_style_normal" /></button>
        <button title="Bus (busbar / manifold)" onClick={() => setDrawingStyle('BUS')} style={{ backgroundColor: drawingStyle === 'BUS' ? COLOR_RUN : 'transparent', color: drawingStyle === 'BUS' ? COLOR_WHITE : undefined }}><StudioIcon name="wire_style_bus" /></button>
      </div>

      <div className="toolbar-group">
        <button title="Direct (the user places every bend by hand)" onClick={() => setWireRoutingMode('STRAIGHT')} style={{ backgroundColor: wireRoutingMode === 'STRAIGHT' ? COLOR_RUN : 'transparent', color: wireRoutingMode === 'STRAIGHT' ? COLOR_WHITE : undefined }}><StudioIcon name="routing_direct" /></button>
        <button title="Avoid (route computed automatically around obstacles)" onClick={() => setWireRoutingMode('AVOID')} style={{ backgroundColor: wireRoutingMode === 'AVOID' ? COLOR_RUN : 'transparent', color: wireRoutingMode === 'AVOID' ? COLOR_WHITE : undefined }}><StudioIcon name="routing_avoid" /></button>
      </div>

      <div className="toolbar-divider" />

      <div className="toolbar-group">
        <button title="Bring to Front" onClick={bringToFront}><StudioIcon name="bring_front" /></button>
        <button title="Send to Back" onClick={sendToBack}><StudioIcon name="send_back" /></button>
      </div>

      <div className="toolbar-divider" />

      <div className="toolbar-group">
        <button title="Lock" onClick={lockSelected}><StudioIcon name="lock" /></button>
        <button title="Unlock" onClick={unlockSelected}><StudioIcon name="unlock" /></button>
      </div>

      <div className="toolbar-divider" />

      <div className="toolbar-group">
        <button title="Rotate Left" onClick={() => rotateSelected('ccw')}><StudioIcon name="rotate_left" /></button>
        <button title="Rotate Right" onClick={() => rotateSelected('cw')}><StudioIcon name="rotate_right" /></button>
      </div>
    </div>
  );
};
