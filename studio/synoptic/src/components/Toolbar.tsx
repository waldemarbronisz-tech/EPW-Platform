// The editor's toolbar: the basics, the work-mode switch, and the tools
// of the current mode - grouped with dividers.
//
//   Undo Redo | Copy Paste Delete | Preview || SYMBOLS ROOMS CONNECTIONS ANNOTATIONS || tools of the mode
//
// A mode decides what a click can reach (project/WorkModes.ts), so the
// tools that go with it live beside the switch and change with it:
//
//   SYMBOLS      front / back | lock / unlock | rotate
//   ROOMS        wall, room | frame, building outline | rotate
//   CONNECTIONS  wire | medium | wire style | routing
//   ANNOTATIONS  text box
//
// Inside Studio this bar is hidden and Studio's own toolbar shows the
// same buttons (studio/shell/menus.py). Every button carries a stable
// data-cmd, which is what Studio clicks - titles are translated and may
// change with the language, commands do not.

import React from 'react';
import { useStore } from '../store';
import type { SynopticConnection } from '../store';
import { StudioIcon } from './icons/StudioIcon';
import { insertTextBox } from './insertTextBox';
import { tr } from '../i18n/tr';
import { WORK_MODES, workModeTitle } from '../project/WorkModes';
import { COLOR_ENERGIZED, COLOR_RUN, COLOR_WATER, COLOR_WHITE, VENTILATION_ACTIVE } from '../theme/ScadaTheme';

const MEDIUM_OPTIONS: { value: SynopticConnection['medium']; titleKey: string; icon: string; color: string }[] = [
  { value: 'ELECTRICAL', titleKey: 'tool.medium_electrical', icon: 'medium_electrical', color: COLOR_ENERGIZED },
  { value: 'WATER', titleKey: 'tool.medium_water', icon: 'medium_water', color: COLOR_WATER },
  { value: 'VENTILATION', titleKey: 'tool.medium_ventilation', icon: 'medium_ventilation', color: VENTILATION_ACTIVE },
];

const pressedStyle = (on: boolean, color: string = COLOR_RUN): React.CSSProperties =>
  on ? { backgroundColor: color, color: COLOR_WHITE } : { backgroundColor: 'transparent' };

interface ToolButtonProps {
  cmd: string;
  title: string;
  icon: string;
  onClick: (e: React.MouseEvent) => void;
  pressed?: boolean;
  color?: string;
}

const ToolButton: React.FC<ToolButtonProps> = ({ cmd, title, icon, onClick, pressed, color }) => (
  <button
    data-cmd={cmd}
    title={title}
    aria-pressed={pressed === undefined ? undefined : pressed}
    onClick={onClick}
    style={pressed === undefined ? undefined : pressedStyle(pressed, color)}
  >
    <StudioIcon name={icon} />
  </button>
);

const Divider: React.FC = () => <div className="toolbar-divider" />;

export const Toolbar: React.FC = () => {
  const {
    undo, redo, copySelected, paste, deleteObjects, selectedIds, selectedConnectionIds,
    bringToFront, sendToBack, lockSelected, unlockSelected, rotateSelected,
    selectedMeterIds, selectedSignalPanelIds, selectedFrameIds,
    selectedGroupCommandIds, selectedSetpointPanelIds, selectedWallIds,
    previewMode, setPreviewMode,
    workMode, setWorkMode,
    isDrawingConnection, setDrawingMode,
    drawingMedium, setDrawingMedium, drawingStyle, setDrawingStyle,
    wireRoutingMode, setWireRoutingMode,
    isDrawingFrame, drawingFrameVariant, setDrawingFrameMode,
    isDrawingWall, setDrawingWallMode, isDrawingRoom, setDrawingRoomMode,
  } = useStore();

  return (
    <div className="toolbar">
      <div className="toolbar-group">
        <ToolButton cmd="undo" title={tr('tool.undo')} icon="undo" onClick={undo} />
        <ToolButton cmd="redo" title={tr('tool.redo')} icon="redo" onClick={redo} />
      </div>
      <Divider />
      <div className="toolbar-group">
        <ToolButton cmd="copy" title={tr('tool.copy')} icon="copy" onClick={copySelected} />
        <ToolButton cmd="paste" title={tr('tool.paste')} icon="paste" onClick={paste} />
        <ToolButton
          cmd="delete"
          title={tr('tool.delete')}
          icon="delete"
          onClick={() => deleteObjects(selectedIds, selectedConnectionIds, selectedMeterIds, selectedSignalPanelIds, selectedFrameIds, selectedGroupCommandIds, selectedSetpointPanelIds, selectedWallIds)}
        />
      </div>
      <Divider />
      <div className="toolbar-group">
        <ToolButton cmd="preview" title={tr('tool.preview')} icon="preview_mode" pressed={previewMode} onClick={() => setPreviewMode(!previewMode)} />
      </div>
      <Divider />

      {/* The work-mode switch: four mutually exclusive, named buttons. */}
      <div className="toolbar-group toolbar-modes" role="radiogroup" aria-label={tr('mode.group_title')}>
        {WORK_MODES.map(mode => (
          <button
            key={mode}
            data-cmd={`mode:${mode}`}
            role="radio"
            aria-checked={workMode === mode}
            title={workModeTitle(mode)}
            onClick={() => setWorkMode(mode)}
            className={workMode === mode ? 'toolbar-mode toolbar-mode-active' : 'toolbar-mode'}
            style={pressedStyle(workMode === mode)}
          >
            {tr(`mode.${mode}`)}
          </button>
        ))}
      </div>
      <Divider />

      {workMode === 'SYMBOLS' && (
        <>
          <div className="toolbar-group">
            <ToolButton cmd="bring_front" title={tr('tool.bring_front')} icon="bring_front" onClick={bringToFront} />
            <ToolButton cmd="send_back" title={tr('tool.send_back')} icon="send_back" onClick={sendToBack} />
          </div>
          <Divider />
          <div className="toolbar-group">
            <ToolButton cmd="lock" title={tr('tool.lock')} icon="lock" onClick={lockSelected} />
            <ToolButton cmd="unlock" title={tr('tool.unlock')} icon="unlock" onClick={unlockSelected} />
          </div>
          <Divider />
          <div className="toolbar-group">
            <ToolButton cmd="rotate_left" title={tr('tool.rotate_left')} icon="rotate_left" onClick={() => rotateSelected('ccw')} />
            <ToolButton cmd="rotate_right" title={tr('tool.rotate_right')} icon="rotate_right" onClick={() => rotateSelected('cw')} />
          </div>
        </>
      )}

      {workMode === 'ROOMS' && (
        <>
          <div className="toolbar-group">
            <ToolButton cmd="draw_wall" title={tr('tool.draw_wall_title')} icon="draw_wall" pressed={isDrawingWall} onClick={() => setDrawingWallMode(!isDrawingWall)} />
            <ToolButton cmd="draw_room" title={tr('tool.draw_room_title')} icon="draw_room" pressed={isDrawingRoom} onClick={() => setDrawingRoomMode(!isDrawingRoom)} />
          </div>
          <Divider />
          <div className="toolbar-group">
            <ToolButton
              cmd="draw_frame"
              title={tr('tool.draw_frame_title')}
              icon="draw_frame"
              pressed={isDrawingFrame && drawingFrameVariant === 'PLAIN'}
              onClick={e => setDrawingFrameMode(!(isDrawingFrame && drawingFrameVariant === 'PLAIN'), 'PLAIN', e.shiftKey)}
            />
            <ToolButton
              cmd="draw_building"
              title={tr('tool.draw_building_title')}
              icon="draw_building"
              pressed={isDrawingFrame && drawingFrameVariant === 'BUILDING'}
              onClick={e => setDrawingFrameMode(!(isDrawingFrame && drawingFrameVariant === 'BUILDING'), 'BUILDING', e.shiftKey)}
            />
          </div>
          <Divider />
          {/* Rotation belongs to laying out a room as much as to
              arranging symbols (owner, 2026-09-20): a door, a table or
              a luminaire is turned WHILE the plan is being drawn, and
              having to leave the mode to do it was the whole friction.
              Same rotateSelected, same data-cmd - Studio's toolbar
              mirrors this pair into its own ROOMS group. */}
          <div className="toolbar-group">
            <ToolButton cmd="rotate_left" title={tr('tool.rotate_left')} icon="rotate_left" onClick={() => rotateSelected('ccw')} />
            <ToolButton cmd="rotate_right" title={tr('tool.rotate_right')} icon="rotate_right" onClick={() => rotateSelected('cw')} />
          </div>
        </>
      )}

      {workMode === 'CONNECTIONS' && (
        <>
          <div className="toolbar-group">
            <ToolButton cmd="draw_wire" title={tr('tool.draw_wire')} icon="draw_wire" pressed={isDrawingConnection} onClick={() => setDrawingMode(!isDrawingConnection)} />
          </div>
          <Divider />
          <div className="toolbar-group">
            {MEDIUM_OPTIONS.map(({ value, titleKey, icon, color }) => (
              <ToolButton
                key={value}
                cmd={`medium:${value}`}
                title={tr(titleKey)}
                icon={icon}
                pressed={drawingMedium === value}
                color={color}
                onClick={() => setDrawingMedium(value)}
              />
            ))}
          </div>
          <Divider />
          <div className="toolbar-group">
            <ToolButton cmd="style:NORMAL" title={tr('tool.style_normal')} icon="wire_style_normal" pressed={drawingStyle === 'NORMAL'} onClick={() => setDrawingStyle('NORMAL')} />
            <ToolButton cmd="style:BUS" title={tr('tool.style_bus')} icon="wire_style_bus" pressed={drawingStyle === 'BUS'} onClick={() => setDrawingStyle('BUS')} />
          </div>
          <Divider />
          <div className="toolbar-group">
            <ToolButton cmd="routing:STRAIGHT" title={tr('tool.routing_direct')} icon="routing_direct" pressed={wireRoutingMode === 'STRAIGHT'} onClick={() => setWireRoutingMode('STRAIGHT')} />
            <ToolButton cmd="routing:AVOID" title={tr('tool.routing_avoid')} icon="routing_avoid" pressed={wireRoutingMode === 'AVOID'} onClick={() => setWireRoutingMode('AVOID')} />
          </div>
        </>
      )}

      {workMode === 'ANNOTATIONS' && (
        <div className="toolbar-group">
          <ToolButton cmd="text_box" title={tr('tool.text_box')} icon="text_box" onClick={insertTextBox} />
        </div>
      )}
    </div>
  );
};
