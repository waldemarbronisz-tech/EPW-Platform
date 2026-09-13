// feat/multi-screen: the strip of screens, above the canvas.
//
// A tab bar rather than a dropdown, deliberately: a controller's screens
// are few and switched constantly, and the one question this has to
// answer at a glance is "which rooms exist, and which am I on". A
// dropdown hides both answers behind a click.
//
// Double-click a tab to rename it in place - the same edit-in-place
// gesture ObjectLabelRenderer already uses for a label, so the editor
// has one way of renaming things rather than two.

import React, { useState } from 'react';
import { useStore } from '../store';
import { ViewMenu } from './ViewMenu';
import {
  COLOR_BEVEL_DARK, COLOR_BEVEL_LIGHT, COLOR_OUTLINE, COLOR_PANEL,
  FONT_SIZE_BASE, FONT_UI,
} from '../theme/ScadaTheme';

const barStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'stretch',
  gap: 2,
  padding: '2px 4px',
  background: COLOR_PANEL,
  borderBottom: `1px solid ${COLOR_BEVEL_DARK}`,
  fontFamily: FONT_UI,
  fontSize: FONT_SIZE_BASE,
  flexWrap: 'wrap',
};

function tabStyle(active: boolean): React.CSSProperties {
  return {
    display: 'flex',
    alignItems: 'center',
    gap: 4,
    padding: '2px 8px',
    cursor: 'pointer',
    background: active ? COLOR_BEVEL_LIGHT : COLOR_PANEL,
    // The raised/sunken bevel pair this whole editor's chrome is drawn
    // with - an active tab reads as pressed in, as it does everywhere
    // else here.
    borderTop: `1px solid ${active ? COLOR_BEVEL_DARK : COLOR_BEVEL_LIGHT}`,
    borderLeft: `1px solid ${active ? COLOR_BEVEL_DARK : COLOR_BEVEL_LIGHT}`,
    borderRight: `1px solid ${active ? COLOR_BEVEL_LIGHT : COLOR_BEVEL_DARK}`,
    borderBottom: `1px solid ${active ? COLOR_BEVEL_LIGHT : COLOR_BEVEL_DARK}`,
    fontWeight: active ? 'bold' : 'normal',
    color: COLOR_OUTLINE,
    whiteSpace: 'nowrap',
  };
}

export const ScreenTabs: React.FC = () => {
  const screens = useStore(s => s.screens);
  const activeScreenId = useStore(s => s.activeScreenId);
  const switchScreen = useStore(s => s.switchScreen);
  const addScreen = useStore(s => s.addScreen);
  const renameScreen = useStore(s => s.renameScreen);
  const deleteScreen = useStore(s => s.deleteScreen);

  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState('');

  const startRename = (id: string, current: string) => {
    setEditingId(id);
    setDraft(current);
  };

  const commitRename = () => {
    if (editingId) renameScreen(editingId, draft);
    setEditingId(null);
  };

  return (
    <div style={barStyle}>
      {screens.map(screen => {
        const active = screen.id === activeScreenId;
        if (editingId === screen.id) {
          return (
            <input
              key={screen.id}
              autoFocus
              value={draft}
              onChange={e => setDraft(e.target.value)}
              onBlur={commitRename}
              onKeyDown={e => {
                if (e.key === 'Enter') commitRename();
                // Escape abandons the edit rather than committing a
                // half-typed name.
                if (e.key === 'Escape') setEditingId(null);
              }}
              style={{ width: 120 }}
            />
          );
        }
        return (
          <div
            key={screen.id}
            style={tabStyle(active)}
            onClick={() => switchScreen(screen.id)}
            onDoubleClick={() => startRename(screen.id, screen.name)}
            title="Click to make active. Double-click to rename."
          >
            <span>{screen.name}</span>
            {/* The close cross only on the active tab: closing a screen
                you are not looking at is a keystroke away from closing
                the wrong one, and there is no visual confirmation of
                what vanished. */}
            {active && screens.length > 1 && (
              <button
                onClick={e => {
                  e.stopPropagation();
                  if (window.confirm(`Delete screen "${screen.name}" and everything on it?`)) {
                    deleteScreen(screen.id);
                  }
                }}
                title="Delete this screen"
                style={{ padding: '0 4px', lineHeight: 1 }}
              >
                x
              </button>
            )}
          </div>
        );
      })}

      <button onClick={() => addScreen()} title="Add a new, empty screen" style={{ padding: '0 8px' }}>
        + Screen
      </button>

      {/* Pushed to the right: the tabs say WHICH screen, this says how
          many of them are on show and how they are arranged. Next to
          what it changes, rather than up in the menu bar. */}
      <span style={{ flex: 1 }} />
      <ViewMenu />
    </div>
  );
};
