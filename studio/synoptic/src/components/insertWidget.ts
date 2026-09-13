// feat/synoptic-library: inserting a screen panel - a meter panel, a
// signal panel, a group command button or a setpoint panel - from the
// Object Library, by a click or by dropping it on the canvas.
//
// These are not symbols (each has its own element array), but they are
// inserted like symbols and bound to devices like symbols, so they sit in
// the library with them and put the editor in the SYMBOLS work mode.

import { useStore } from '../store';
import { METER_DEFAULT_FONT_SIZE } from '../meter/MeterElement';
import { SIGNAL_PANEL_DEFAULT_FONT_SIZE } from '../elements/SignalPanelElement';
import { GROUP_COMMAND_DEFAULT_WIDTH } from '../elements/GroupCommandElement';
import { SETPOINT_DEFAULT_FONT_SIZE } from '../elements/SetpointElement';
import type { WidgetType } from '../project/LibraryDomains';
import { tr } from '../i18n/tr';

/** Where a panel inserted by a click lands: a little in from the top-left corner of what is on screen, on the grid. */
function visibleCorner(): { x: number; y: number } {
  const { zoom, panX, panY } = useStore.getState().canvasState;
  return {
    x: Math.round((-panX + 160) / zoom / 16) * 16,
    y: Math.round((-panY + 160) / zoom / 16) * 16,
  };
}

/** Inserts the panel at (x, y) - or near the top-left of the view - selects it and records it as recently used. */
export function insertWidget(type: WidgetType, x?: number, y?: number): void {
  const at = x === undefined || y === undefined ? visibleCorner() : { x, y };
  const store = useStore.getState();
  store.setWorkMode('SYMBOLS');
  store.recordSymbolUse(type);
  switch (type) {
    case 'widget.meter': {
      store.addMeter({ ...at, width: 200, fontSize: METER_DEFAULT_FONT_SIZE, rows: [] });
      const newest = useStore.getState().meters.at(-1);
      if (newest) useStore.getState().selectMeters([newest.id], false);
      break;
    }
    case 'widget.signal_panel': {
      store.addSignalPanel({ ...at, width: 160, fontSize: SIGNAL_PANEL_DEFAULT_FONT_SIZE, rows: [] });
      const newest = useStore.getState().signalPanels.at(-1);
      if (newest) useStore.getState().selectSignalPanels([newest.id], false);
      break;
    }
    case 'widget.group_command': {
      store.addGroupCommand({ ...at, width: GROUP_COMMAND_DEFAULT_WIDTH, label: tr('widget.new_button_label'), command: 'CLOSE', deviceIds: [] });
      const newest = useStore.getState().groupCommands.at(-1);
      if (newest) useStore.getState().selectGroupCommands([newest.id], false);
      break;
    }
    case 'widget.setpoint_panel': {
      store.addSetpointPanel({ ...at, width: 200, fontSize: SETPOINT_DEFAULT_FONT_SIZE, rows: [] });
      const newest = useStore.getState().setpointPanels.at(-1);
      if (newest) useStore.getState().selectSetpointPanels([newest.id], false);
      break;
    }
  }
}
