// Panel preview: the whole window is the panel. One screen, drawn by the
// same Canvas the editor uses but the way runtime's page draws it (no
// grid, the runtime frame or everything drawn fitted), operable by
// clicking - live through the controller when Studio's "Na żywo" is on,
// in the simulation otherwise. Esc, or the button, returns to editing.
//
// Studio wraps this in a full-screen window of its own (F11 there): it
// hides its tree and toolbars and asks for this through
// window.__synopticPanelPreview, then reads __synopticStudioState().
// panelPreview to know when Esc was pressed here.

import React, { useEffect } from 'react';
import { useStore } from '../store';
import { Canvas } from './Canvas';
import { tr } from '../i18n/tr';
import {
  COLOR_BEVEL_DARK, COLOR_BEVEL_LIGHT, COLOR_OUTLINE, COLOR_PANEL, FONT_SIZE_SMALL, FONT_UI,
} from '../theme/ScadaTheme';

const barStyle: React.CSSProperties = {
  position: 'absolute',
  top: 8,
  right: 8,
  zIndex: 10,
  display: 'flex',
  alignItems: 'center',
  gap: 8,
  padding: '4px 8px',
  background: COLOR_PANEL,
  border: `1px solid ${COLOR_OUTLINE}`,
  borderTop: `1px solid ${COLOR_BEVEL_LIGHT}`,
  borderLeft: `1px solid ${COLOR_BEVEL_LIGHT}`,
  boxShadow: '2px 2px 6px rgba(0,0,0,0.4)',
  fontFamily: FONT_UI,
  fontSize: FONT_SIZE_SMALL,
  color: COLOR_OUTLINE,
  opacity: 0.92,
};

export const PanelPreview: React.FC = () => {
  const preview = useStore(s => s.panelPreview);
  const screens = useStore(s => s.screens);
  const live = useStore(s => s.liveValues !== null);
  const background = useStore(s => s.canvasConfig.background);
  const exitPanelPreview = useStore(s => s.exitPanelPreview);
  const enterPanelPreview = useStore(s => s.enterPanelPreview);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { e.preventDefault(); exitPanelPreview(); }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [exitPanelPreview]);

  if (!preview) return null;

  return (
    <div
      className="panel-preview"
      style={{ position: 'fixed', inset: 0, zIndex: 900, background, display: 'flex', flexDirection: 'column' }}
    >
      <div style={barStyle}>
        <span style={{ fontWeight: 'bold', color: live ? '#1a7f1a' : COLOR_OUTLINE }}>
          {live ? tr('preview.live') : tr('preview.simulation')}
        </span>
        <span style={{ borderLeft: `1px solid ${COLOR_BEVEL_DARK}`, height: 14 }} />
        {screens.length > 1 ? (
          <select
            value={preview.screenId}
            onChange={e => enterPanelPreview(e.target.value)}
            title={tr('preview.screen_hint')}
            style={{ fontFamily: FONT_UI, fontSize: FONT_SIZE_SMALL }}
          >
            {screens.map(screen => (
              <option key={screen.id} value={screen.id}>{screen.name || screen.id}</option>
            ))}
          </select>
        ) : (
          <span>{screens[0]?.name || preview.screenId}</span>
        )}
        <button onClick={exitPanelPreview} title={tr('preview.close_hint')} style={{ padding: '0 8px' }}>
          {tr('preview.close')}
        </button>
      </div>
      {/* A flex column: .canvas-container is `flex: 1` and only fills a flex parent. */}
      <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
        <Canvas />
      </div>
    </div>
  );
};
