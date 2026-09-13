// feat/text-formatting: inserting a text box from a button - the format
// bar's "Text box" and the SCADA library entry share this. Kept out of
// the component files so they export components only (fast refresh).

import { useStore } from '../store';
import { TEXT_BOX_TYPE } from '../project/TextFormatting';
import { getSymbolDefinition } from '../symbols/SymbolRegistry';
import { FONT_SIZE_BASE, FONT_UI } from '../theme/ScadaTheme';

/** Places a new, empty text box in the visible part of the canvas and opens it for typing. */
export function insertTextBox(): void {
  const state = useStore.getState();
  const def = getSymbolDefinition(TEXT_BOX_TYPE);
  const { zoom, panX, panY } = state.canvasState;
  const x = Math.round((-panX + 80) / zoom / 16) * 16;
  const y = Math.round((-panY + 80) / zoom / 16) * 16;
  state.addObject({
    type: TEXT_BOX_TYPE,
    category: def?.category || 'SCADA',
    x, y,
    width: def?.defaultWidth || 240,
    height: def?.defaultHeight || 48,
    rotation: 0, scaleX: 1, scaleY: 1,
    visible: true, locked: false, layer: 1,
    tag: '', description: '',
    color: '', fill: '', border: '',
    text: '',
    font: FONT_UI,
    fontSize: FONT_SIZE_BASE,
    textStyle: 'normal',
    textAlign: 'left',
    // Whatever the format bar was set to with nothing selected.
    ...state.nextTextFormat,
    editor: { preview_state: '' },
    tooltip: '',
    customProperties: {},
  });
  const created = useStore.getState().objects[useStore.getState().objects.length - 1];
  if (created) {
    useStore.getState().selectObjects([created.id]);
    useStore.getState().setEditingTextId(created.id);
  }
}
