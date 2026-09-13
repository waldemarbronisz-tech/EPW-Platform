/** @vitest-environment jsdom */
// feat/synoptic-modes: work modes - SYMBOLS, ROOMS, CONNECTIONS, ANNOTATIONS.
//
// The point of a mode is what a click CAN'T reach: drawing a room must not
// pick up the valve under the cursor, a marquee round a room must not take
// its luminaires. These tests check that content - which kinds each mode
// reaches, what a selection keeps, what Ctrl+A takes, what arming a tool
// does - not merely that the functions exist.

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup, fireEvent, act } from '@testing-library/react';
import {
  isKindActive, modeFromShortcut, objectKind, restrictSelectionToMode, WORK_MODES, WORK_MODE_SHORTCUTS, workModeTitle,
} from '../project/WorkModes';
import { editorShortcut } from '../utils/EditorShortcuts';
import { useStore } from '../store';
import type { SynopticObject } from '../store';
import { Toolbar } from '../components/Toolbar';
import { setLanguage } from '../i18n/tr';

const obj = (id: string, type: string): SynopticObject => ({
  id, type, category: 'X', x: 0, y: 0, rotation: 0, scaleX: 1, scaleY: 1,
  visible: true, locked: false, layer: 1, tag: '', description: '',
  color: '', fill: '', border: '', text: '', font: 'Tahoma', fontSize: 13,
  tooltip: '', width: 64, height: 64, customProperties: {},
});

const wall = (id: string) => ({ id, from: { x: 0, y: 0 }, to: { x: 160, y: 0 }, thickness: 12, height: 40, material: 'brick' }) as never;
const frame = (id: string) => ({ id, x: 0, y: 0, width: 320, height: 240, titlePosition: 'TOP_LEFT', variant: 'PLAIN' }) as never;

const selection = {
  objectIds: ['valve', 'label'],
  connectionIds: ['wire'],
  meterIds: ['meter'],
  signalPanelIds: [],
  frameIds: ['frame'],
  groupCommandIds: [],
  setpointPanelIds: [],
  wallIds: ['w1', 'w2'],
};
const objects = [obj('valve', 'water.ball_valve'), obj('label', 'scada.text_box')];

beforeEach(() => {
  setLanguage('en');
  useStore.setState({
    objects: [obj('valve', 'water.ball_valve'), obj('label', 'scada.text_box')],
    connections: [{ id: 'wire', points: [{ x: 0, y: 0 }, { x: 64, y: 0 }], medium: 'ELECTRICAL', style: 'NORMAL' } as never],
    meters: [], signalPanels: [], groupCommands: [], setpointPanels: [],
    walls: [wall('w1'), wall('w2')],
    frames: [frame('frame')],
    workMode: 'SYMBOLS',
    isDrawingConnection: false, isDrawingWall: false, isDrawingRoom: false, isDrawingFrame: false,
    selectedIds: [], selectedConnectionIds: [], selectedMeterIds: [], selectedSignalPanelIds: [],
    selectedFrameIds: [], selectedGroupCommandIds: [], selectedSetpointPanelIds: [], selectedWallIds: [],
  });
});
afterEach(cleanup);

describe('what each mode can reach', () => {
  it('splits the four modes into disjoint kinds: symbols and panels / walls and frames / wires / text', () => {
    expect(isKindActive('SYMBOLS', 'symbol')).toBe(true);
    expect(isKindActive('SYMBOLS', 'meter')).toBe(true);
    expect(isKindActive('SYMBOLS', 'wall')).toBe(false);
    expect(isKindActive('ROOMS', 'wall')).toBe(true);
    expect(isKindActive('ROOMS', 'frame')).toBe(true);
    expect(isKindActive('ROOMS', 'symbol')).toBe(false);
    expect(isKindActive('CONNECTIONS', 'connection')).toBe(true);
    expect(isKindActive('CONNECTIONS', 'symbol')).toBe(false);
    expect(isKindActive('ANNOTATIONS', 'annotation')).toBe(true);
    expect(isKindActive('ANNOTATIONS', 'symbol')).toBe(false);
  });

  it('treats text boxes, labels and plain shapes as annotations and everything else as symbols', () => {
    expect(objectKind('scada.text_box')).toBe('annotation');
    expect(objectKind('graphics.rectangle')).toBe('annotation');
    expect(objectKind('scada.label_frame')).toBe('annotation');
    expect(objectKind('water.ball_valve')).toBe('symbol');
    expect(objectKind('building.door')).toBe('symbol');
  });

  it('a ROOMS marquee keeps the walls and the frame and drops the valve, the label, the wire and the meter', () => {
    expect(restrictSelectionToMode(selection, objects, 'ROOMS')).toEqual({
      objectIds: [], connectionIds: [], meterIds: [], signalPanelIds: [], frameIds: ['frame'],
      groupCommandIds: [], setpointPanelIds: [], wallIds: ['w1', 'w2'],
    });
    expect(restrictSelectionToMode(selection, objects, 'SYMBOLS').objectIds).toEqual(['valve']);
    expect(restrictSelectionToMode(selection, objects, 'ANNOTATIONS').objectIds).toEqual(['label']);
  });
});

describe('keyboard', () => {
  it('Ctrl+1..4 switch modes in switcher order; a plain digit or Ctrl+Shift+digit does not', () => {
    expect(WORK_MODES.map(mode => WORK_MODE_SHORTCUTS[mode])).toEqual(['Ctrl+1', 'Ctrl+2', 'Ctrl+3', 'Ctrl+4']);
    expect(modeFromShortcut({ key: '2', ctrlKey: true })).toBe('ROOMS');
    expect(modeFromShortcut({ key: '4', ctrlKey: true })).toBe('ANNOTATIONS');
    expect(modeFromShortcut({ key: '1', ctrlKey: false })).toBeNull();
    expect(modeFromShortcut({ key: '1', ctrlKey: true, shiftKey: true })).toBeNull();
    expect(editorShortcut({ key: '3', ctrlKey: true })).toEqual({ kind: 'mode', mode: 'CONNECTIONS' });
  });

  it('the switcher tooltip names the mode, its shortcut and what it selects - in Polish too', () => {
    expect(workModeTitle('ROOMS')).toContain('Ctrl+2');
    expect(workModeTitle('ROOMS')).toContain('walls');
    setLanguage('pl');
    expect(workModeTitle('ROOMS')).toContain('Pomieszczenia');
    expect(workModeTitle('ROOMS')).toContain('ściany');
    setLanguage('en');
  });
});

describe('the store', () => {
  it('switching to ROOMS puts the wire tool down and keeps only the walls of the selection', () => {
    useStore.setState({ isDrawingConnection: true, selectedIds: ['valve'], selectedWallIds: ['w1'] });
    useStore.getState().setWorkMode('ROOMS');
    const s = useStore.getState();
    expect(s.workMode).toBe('ROOMS');
    expect(s.isDrawingConnection).toBe(false);
    expect(s.selectedIds).toEqual([]);
    expect(s.selectedWallIds).toEqual(['w1']);
  });

  it('arming a tool switches to the mode it draws in', () => {
    useStore.getState().setDrawingWallMode(true);
    expect(useStore.getState().workMode).toBe('ROOMS');
    useStore.getState().setDrawingMode(true);
    expect(useStore.getState().workMode).toBe('CONNECTIONS');
    expect(useStore.getState().isDrawingWall).toBe(false);
    useStore.getState().setDrawingFrameMode(true, 'BUILDING');
    expect(useStore.getState().workMode).toBe('ROOMS');
  });

  it('Ctrl+A takes only what the mode reaches', () => {
    useStore.getState().setWorkMode('ROOMS');
    useStore.getState().selectAll();
    let s = useStore.getState();
    expect(s.selectedWallIds).toEqual(['w1', 'w2']);
    expect(s.selectedFrameIds).toEqual(['frame']);
    expect(s.selectedIds).toEqual([]);
    expect(s.selectedConnectionIds).toEqual([]);

    useStore.getState().setWorkMode('SYMBOLS');
    useStore.getState().selectAll();
    s = useStore.getState();
    expect(s.selectedIds).toEqual(['valve']);
    expect(s.selectedWallIds).toEqual([]);
  });
});

describe('the toolbar', () => {
  it('shows the four modes as one exclusive group, marks the active one, and changes its tools with the mode', () => {
    render(<Toolbar />);
    const radios = screen.getAllByRole('radio');
    expect(radios.map(r => r.textContent)).toEqual(['Symbols', 'Rooms', 'Connections', 'Annotations']);
    expect(radios.filter(r => r.getAttribute('aria-checked') === 'true').map(r => r.textContent)).toEqual(['Symbols']);
    const cmds = () => Array.from(document.querySelectorAll('[data-cmd]')).map(b => b.getAttribute('data-cmd'));
    expect(cmds()).toContain('rotate_left');
    expect(cmds()).not.toContain('draw_wall');

    act(() => { fireEvent.click(screen.getByRole('radio', { name: 'Rooms' })); });
    expect(useStore.getState().workMode).toBe('ROOMS');
    expect(cmds()).toContain('draw_wall');
    expect(cmds()).toContain('draw_room');
    expect(cmds()).not.toContain('draw_wire');
    expect(cmds()).not.toContain('rotate_left');

    act(() => { fireEvent.click(screen.getByRole('radio', { name: 'Connections' })); });
    expect(cmds()).toEqual(expect.arrayContaining(['draw_wire', 'medium:WATER', 'style:BUS', 'routing:AVOID']));
    expect(cmds()).not.toContain('draw_wall');
  });
});
