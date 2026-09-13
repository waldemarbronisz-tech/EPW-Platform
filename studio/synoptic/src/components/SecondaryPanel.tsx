// feat/workspace: the lower panel - the tools for the screen being
// worked on.
//
// It began as the message log and nothing else, which is a lot of
// permanent height for a panel that is empty most of the time. Then it
// briefly hosted a second screen, and that turned out to be the wrong
// home for one: seeing several rooms at once is a job for the drawing
// area itself, which is what ScreenWorkspace now does. What belongs down
// here is the other thing: everything you want to know ABOUT the screen
// you are drawing on, without a modal covering it.
//
// So the panel is scoped to the ACTIVE screen, and says so in its own
// header - switch screens in the workspace above and every tab here
// follows. Four questions, in the order they come up while working:
//
//   Kompilacja  - could this be handed to a controller at all?
//   Symulacja   - what will it do when an operator touches it?
//   Oswietlenie - is the room bright enough?
//   Zestawienie - how much of everything is there?
//   Komunikaty  - the editor's own log, unchanged.
//
// The compilation tab carries the error count in its own label, because
// an error list nobody opens is not a check - it has to be visible
// without clicking.

import React, { useMemo, useState } from 'react';
import { useStore } from '../store';
import { MessagesPanel } from './MessagesPanel';
import { CompilationPanel } from './CompilationPanel';
import { SimulationPanel } from './SimulationPanel';
import { LightingPanel } from './LightingPanel';
import { TakeoffPanel } from './TakeoffPanel';
import { validateScreen } from '../project/ScreenValidation';
import {
  COLOR_ALARM, COLOR_BEVEL_DARK, COLOR_BEVEL_LIGHT, COLOR_OUTLINE, COLOR_PANEL,
  COLOR_RUN, FONT_SIZE_SMALL, FONT_UI, VENTILATION_ACTIVE,
} from '../theme/ScadaTheme';

type TabId = 'compilation' | 'simulation' | 'lighting' | 'takeoff' | 'messages';

const headerStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'stretch',
  gap: 2,
  padding: '2px 4px',
  background: COLOR_PANEL,
  borderBottom: `1px solid ${COLOR_BEVEL_DARK}`,
  fontFamily: FONT_UI,
  fontSize: FONT_SIZE_SMALL,
  color: COLOR_OUTLINE,
};

function tabStyle(active: boolean): React.CSSProperties {
  return {
    display: 'flex',
    alignItems: 'center',
    gap: 5,
    padding: '2px 10px',
    cursor: 'pointer',
    userSelect: 'none',
    background: active ? COLOR_BEVEL_LIGHT : COLOR_PANEL,
    // The same raised/sunken bevel pair the rest of this editor's chrome
    // uses - an active tab reads as pressed in, as it does everywhere.
    borderTop: `1px solid ${active ? COLOR_BEVEL_DARK : COLOR_BEVEL_LIGHT}`,
    borderLeft: `1px solid ${active ? COLOR_BEVEL_DARK : COLOR_BEVEL_LIGHT}`,
    borderRight: `1px solid ${active ? COLOR_BEVEL_LIGHT : COLOR_BEVEL_DARK}`,
    borderBottom: `1px solid ${active ? COLOR_BEVEL_LIGHT : COLOR_BEVEL_DARK}`,
    fontWeight: active ? 'bold' : 'normal',
    whiteSpace: 'nowrap',
  };
}

export const SecondaryPanel: React.FC = () => {
  const screens = useStore(s => s.screens);
  const activeScreenId = useStore(s => s.activeScreenId);
  const objects = useStore(s => s.objects);
  const walls = useStore(s => s.walls);
  const circuits = useStore(s => s.circuits);
  const devices = useStore(s => s.devices);
  const simulationRunning = useStore(s => s.simulationRunning);

  const [tab, setTab] = useState<TabId>('compilation');

  // Only the counts are needed here, but the whole validation is what
  // produces them, and it is memoised on exactly what it reads - the
  // tab labels must not re-run every rule on every unrelated render.
  const validation = useMemo(
    () => validateScreen(objects, walls, circuits, devices),
    [objects, walls, circuits, devices]
  );

  const screenName = screens.find(s => s.id === activeScreenId)?.name ?? '-';

  const tabs: { id: TabId; label: string; badge?: React.ReactNode; title: string }[] = [
    {
      id: 'compilation',
      label: 'Build check',
      title: 'What would stop this screen from being handed to a controller',
      badge: validation.errors > 0
        ? <span style={{ color: COLOR_ALARM, fontWeight: 'bold' }}>{validation.errors}</span>
        : (validation.warnings > 0
          ? <span style={{ color: VENTILATION_ACTIVE, fontWeight: 'bold' }}>{validation.warnings}</span>
          : <span style={{ color: COLOR_RUN, fontWeight: 'bold' }}>OK</span>),
    },
    {
      id: 'simulation',
      label: 'Simulation',
      title: 'Operate circuits with confirmation, as on the controller',
      badge: simulationRunning
        ? <span style={{ color: COLOR_RUN, fontWeight: 'bold' }}>{'●'}</span>
        : undefined,
    },
    { id: 'lighting', label: 'Lighting', title: 'Illuminance calculation results' },
    { id: 'takeoff', label: 'Quantities', title: 'Quantities: walls, floor, devices, circuits' },
    { id: 'messages', label: 'Messages', title: "The editor's message log" },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={headerStyle}>
        {tabs.map(entry => (
          <div
            key={entry.id}
            style={tabStyle(tab === entry.id)}
            onClick={() => setTab(entry.id)}
            title={entry.title}
          >
            <span>{entry.label}</span>
            {entry.badge}
          </div>
        ))}
        <span style={{ flex: 1 }} />
        {/* Which screen these tools are about. Not decoration: with four
            rooms tiled above, a panel that does not name its subject is
            a panel you cannot trust. */}
        <span style={{ display: 'flex', alignItems: 'center', gap: 4, paddingRight: 6 }}>
          <span style={{ opacity: 0.75 }}>Screen:</span>
          <b>{screenName}</b>
        </span>
      </div>

      <div style={{ flex: 1, minHeight: 0 }}>
        {tab === 'compilation' && <CompilationPanel />}
        {tab === 'simulation' && <SimulationPanel />}
        {tab === 'lighting' && <LightingPanel />}
        {tab === 'takeoff' && <TakeoffPanel />}
        {tab === 'messages' && <MessagesPanel />}
      </div>
    </div>
  );
};
