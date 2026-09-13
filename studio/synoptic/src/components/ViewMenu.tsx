// feat/workspace: the "View" control - how the screens are arranged and
// which of them are on the workspace.
//
// It sits in the screen tab bar rather than in the menu bar at the top,
// because it acts on the tabs beside it: a control belongs next to what
// it changes. Every screen is shown by default; this is where one is
// taken off the workspace or brought back.

import React, { useEffect, useRef, useState } from 'react';
import { useStore } from '../store';
import { visibleScreens, WORKSPACE_LAYOUTS } from '../project/WorkspaceLayout';
import {
  COLOR_BEVEL_DARK, COLOR_BEVEL_LIGHT, COLOR_OUTLINE, COLOR_PANEL,
  FONT_SIZE_SMALL, FONT_UI,
} from '../theme/ScadaTheme';

const panelStyle: React.CSSProperties = {
  position: 'absolute',
  top: '100%',
  right: 0,
  zIndex: 40,
  minWidth: 240,
  background: COLOR_PANEL,
  border: `1px solid ${COLOR_OUTLINE}`,
  borderTop: `1px solid ${COLOR_BEVEL_LIGHT}`,
  borderLeft: `1px solid ${COLOR_BEVEL_LIGHT}`,
  boxShadow: '2px 2px 6px rgba(0,0,0,0.4)',
  fontFamily: FONT_UI,
  fontSize: FONT_SIZE_SMALL,
  color: COLOR_OUTLINE,
  padding: 4,
};

const sectionStyle: React.CSSProperties = {
  padding: '3px 6px 2px',
  fontWeight: 'bold',
  borderBottom: `1px solid ${COLOR_BEVEL_DARK}`,
  marginBottom: 2,
};

const rowStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 6,
  padding: '3px 6px',
  cursor: 'pointer',
  whiteSpace: 'nowrap',
};

export const ViewMenu: React.FC = () => {
  const screens = useStore(s => s.screens);
  const activeScreenId = useStore(s => s.activeScreenId);
  const layout = useStore(s => s.workspaceLayout);
  const hiddenScreens = useStore(s => s.hiddenScreens);
  const setWorkspaceLayout = useStore(s => s.setWorkspaceLayout);
  const showScreen = useStore(s => s.showScreen);
  const hideScreen = useStore(s => s.hideScreen);
  const addScreen = useStore(s => s.addScreen);

  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  // Click-away and Escape, both - a dropdown that can only be closed by
  // clicking the button again is a dropdown people leave open by mistake.
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false); };
    window.addEventListener('mousedown', onDown);
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('mousedown', onDown);
      window.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const shownIds = new Set(visibleScreens(hiddenScreens, activeScreenId, layout, screens.map(s => s.id)));

  return (
    <div ref={rootRef} style={{ position: 'relative' }}>
      <button
        onClick={() => setOpen(o => !o)}
        title="Workspace arrangement and visible screens"
        style={{ padding: '0 8px', fontWeight: open ? 'bold' : 'normal' }}
      >
        View {'▾'}
      </button>

      {open && (
        <div style={panelStyle}>
          <div style={sectionStyle}>Arrangement</div>
          {WORKSPACE_LAYOUTS.map(option => (
            <div
              key={option.id}
              style={{
                ...rowStyle,
                background: layout === option.id ? COLOR_BEVEL_LIGHT : 'transparent',
                fontWeight: layout === option.id ? 'bold' : 'normal',
              }}
              title={option.hint}
              onClick={() => setWorkspaceLayout(option.id)}
            >
              <span style={{ width: 12 }}>{layout === option.id ? '•' : ''}</span>
              <span>{option.label}</span>
            </div>
          ))}

          <div style={{ ...sectionStyle, marginTop: 6 }}>Visible screens</div>
          {screens.map(screen => {
            const shown = shownIds.has(screen.id);
            const active = screen.id === activeScreenId;
            return (
              <div
                key={screen.id}
                style={rowStyle}
                title={shown ? 'Hide this screen from the workspace' : 'Show this screen on the workspace'}
                onClick={() => { if (shown) hideScreen(screen.id); else showScreen(screen.id); }}
              >
                <span style={{ width: 12 }}>{shown ? '✓' : ''}</span>
                <span>{screen.name}</span>
                {active && <span style={{ marginLeft: 'auto', opacity: 0.8 }}>active</span>}
              </div>
            );
          })}

          <div style={{ borderTop: `1px solid ${COLOR_BEVEL_DARK}`, marginTop: 4, paddingTop: 2 }}>
            <div
              style={rowStyle}
              onClick={() => { addScreen(); setOpen(false); }}
              title="Add a new, empty screen"
            >
              <span style={{ width: 12 }}>+</span>
              <span>New screen...</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
