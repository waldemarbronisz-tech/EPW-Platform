/** @vitest-environment jsdom */
// feat/synoptic-modes: work modes - SYMBOLS, ROOMS, CONNECTIONS, ANNOTATIONS.
//
// A mode picks the TOOLS on offer (and which options bar shows). It used
// to also decide what a click could reach; user report ("złe
// przemieszczanie, przemieszcza tylko to w jakim trybie jest [...] bez
// względu na tryb edycja była możliwa cały czas") turned that off:
// selecting, marquee, Ctrl+A and moving work on everything in every
// mode. These tests check that content - which kinds each mode offers
// tools for, that nothing is ever excluded from a selection, what Ctrl+A
// takes, what arming a tool does - not merely that the functions exist.

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup, fireEvent, act } from '@testing-library/react';
import {
  isKindActive, isKindOfMode, modeFromShortcut, objectKind, restrictSelectionToMode, WORK_MODES, WORK_MODE_SHORTCUTS,
  workModeTitle,
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
  it('splits the four modes into disjoint TOOL kinds: symbols and panels / walls and frames / wires / text', () => {
    expect(isKindOfMode('SYMBOLS', 'symbol')).toBe(true);
    expect(isKindOfMode('SYMBOLS', 'meter')).toBe(true);
    expect(isKindOfMode('SYMBOLS', 'wall')).toBe(false);
    expect(isKindOfMode('ROOMS', 'wall')).toBe(true);
    expect(isKindOfMode('ROOMS', 'frame')).toBe(true);
    expect(isKindOfMode('ROOMS', 'symbol')).toBe(false);
    expect(isKindOfMode('CONNECTIONS', 'connection')).toBe(true);
    expect(isKindOfMode('CONNECTIONS', 'symbol')).toBe(false);
    expect(isKindOfMode('ANNOTATIONS', 'annotation')).toBe(true);
    expect(isKindOfMode('ANNOTATIONS', 'symbol')).toBe(false);
  });

  it('user report "bez względu na tryb edycja była możliwa cały czas": every kind takes clicks in every mode', () => {
    for (const mode of WORK_MODES) {
      for (const kind of ['symbol', 'annotation', 'wall', 'frame', 'connection', 'meter', 'signalPanel', 'groupCommand', 'setpointPanel'] as const) {
        expect(isKindActive(mode, kind)).toBe(true);
      }
    }
  });

  it('treats text boxes, labels and plain shapes as annotations and everything else as symbols', () => {
    expect(objectKind('scada.text_box')).toBe('annotation');
    expect(objectKind('graphics.rectangle')).toBe('annotation');
    expect(objectKind('scada.label_frame')).toBe('annotation');
    expect(objectKind('water.ball_valve')).toBe('symbol');
    expect(objectKind('building.door')).toBe('symbol');
  });

  it('a marquee keeps everything it caught - walls, frame, valve, label, wire and meter - in every mode', () => {
    for (const mode of WORK_MODES) {
      expect(restrictSelectionToMode(selection, objects, mode)).toEqual(selection);
    }
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
  it('switching to ROOMS puts the wire tool down and leaves the whole selection alone', () => {
    useStore.setState({ isDrawingConnection: true, selectedIds: ['valve'], selectedWallIds: ['w1'] });
    useStore.getState().setWorkMode('ROOMS');
    const s = useStore.getState();
    expect(s.workMode).toBe('ROOMS');
    expect(s.isDrawingConnection).toBe(false);
    expect(s.selectedIds).toEqual(['valve']);
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

  it('Ctrl+A takes everything on the screen, whatever the mode', () => {
    for (const mode of ['ROOMS', 'SYMBOLS'] as const) {
      useStore.getState().setWorkMode(mode);
      useStore.getState().selectAll();
      const s = useStore.getState();
      expect(s.selectedWallIds).toEqual(['w1', 'w2']);
      expect(s.selectedFrameIds).toEqual(['frame']);
      expect(s.selectedIds.sort()).toEqual(['label', 'valve']);
      expect(s.selectedConnectionIds).toEqual(['wire']);
    }
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
