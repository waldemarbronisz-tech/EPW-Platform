/** @vitest-environment jsdom */
// Reported after the modes stage: "a selected room cannot be edited - no
// name, no location, no size". In the running editor Properties said "No
// object selected" with the four walls of a room selected: it only had a
// panel for ONE wall. The chosen way in is Properties.

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, cleanup, fireEvent, screen, act } from '@testing-library/react';
import { useStore } from '../store';
import { ProjectManager } from '../project/ProjectManager';
import { PropertyInspector } from '../components/PropertyInspector';
import { roomLabels, roomSummary } from '../project/AreaMove';
import { PIXELS_PER_METRE } from '../theme/Scale';
import { setLanguage } from '../i18n/tr';

function selectRoom() {
  useStore.getState().addRoomWalls({ x: 160, y: 160, width: 400, height: 240 }); // 5 x 3 m
  const ids = useStore.getState().walls.map(w => w.id);
  useStore.getState().selectWalls(ids);
  return ids;
}

beforeEach(() => {
  setLanguage('en');
  ProjectManager.newProject('Rooms');
  useStore.setState({
    workMode: 'ROOMS',
    locations: [{ code: 'KOT', description: 'Kotlownia' }, { code: 'GAR', description: 'Garaz' }],
  });
});
afterEach(cleanup);

describe('Properties with a room selected', () => {
  it('shows the Room panel - name, location, position, size, measures - not "No object selected"', () => {
    selectRoom();
    render(<PropertyInspector />);
    expect(document.body.textContent).not.toContain('No object selected');
    expect(document.querySelector('[data-inspector="room"]')).not.toBeNull();
    expect((document.querySelector('input[name="roomWidth"]') as HTMLInputElement).value).toBe('5,00');
    expect((document.querySelector('input[name="roomHeight"]') as HTMLInputElement).value).toBe('3,00');
    expect((document.querySelector('input[name="roomPerimeter"]') as HTMLInputElement).value).toBe('16,00 m');
    expect((document.querySelector('input[name="roomFloorArea"]') as HTMLInputElement).value).toBe('15,00 m2');
  });

  it('a name typed there lands on every wall of the room, is one undo step, shows on the floor and survives save and reopen', () => {
    const ids = selectRoom();
    render(<PropertyInspector />);
    const nameBox = document.querySelector('input[name="roomName"]') as HTMLInputElement;
    const history = useStore.getState().historyIndex;
    fireEvent.change(nameBox, { target: { value: 'Kotłownia' } });
    fireEvent.blur(nameBox);
    // ZADANIA p. 6: ONE record, every wall of the room points at it.
    const rooms = useStore.getState().rooms;
    expect(rooms).toHaveLength(1);
    expect(rooms[0].name).toBe('Kotłownia');
    expect(useStore.getState().walls.every(w => w.roomId === rooms[0].id)).toBe(true);
    expect(useStore.getState().historyIndex).toBe(history + 1);
    expect(roomLabels(useStore.getState().walls, useStore.getState().rooms)).toEqual([{ x: 360, y: 280, name: 'Kotłownia', location: '' }]);

    useStore.getState().undo();
    expect(useStore.getState().rooms).toEqual([]);
    expect(useStore.getState().walls.every(w => !w.roomId)).toBe(true);
    useStore.getState().redo();

    // Reopening a project starts a fresh undo history, so this comes last.
    const saved = ProjectManager.getProjectData()!;
    ProjectManager.newProject('Other');
    ProjectManager.loadProject(saved, 'plan.epwsyn');
    expect(roomSummary(useStore.getState().walls, ids, useStore.getState().rooms).name).toBe('Kotłownia');
    expect(useStore.getState().rooms.map(r => r.name)).toEqual(['Kotłownia']);
  });

  it('offers the project locations and stores the chosen code on the room', () => {
    const ids = selectRoom();
    render(<PropertyInspector />);
    const select = document.querySelector('select[name="roomLocation"]') as HTMLSelectElement;
    expect(Array.from(select.options).map(o => o.textContent)).toEqual(['(none)', 'KOT - Kotlownia', 'GAR - Garaz']);
    fireEvent.change(select, { target: { value: 'GAR' } });
    expect(roomSummary(useStore.getState().walls, ids, useStore.getState().rooms).location).toBe('GAR');
  });

  it('a width typed in METRES resizes the room, and X moves it together with a symbol inside', () => {
    // The boxes are metres, not pixels: a person laying out a room
    // knows it is six metres across, not four hundred and eighty
    // pixels. The scale is PIXELS_PER_METRE = 80.
    const ids = selectRoom();
    act(() => {
      useStore.setState({ objects: [{ id: 'valve', type: 'water.ball_valve', category: 'Water', x: 320, y: 256, rotation: 0, scaleX: 1, scaleY: 1, visible: true, locked: false, layer: 1, tag: '', description: '', color: '', fill: '', border: '', text: '', font: '', fontSize: 13, tooltip: '', width: 48, height: 48, customProperties: {} }] });
    });
    render(<PropertyInspector />);
    const width = document.querySelector('input[name="roomWidth"]') as HTMLInputElement;
    fireEvent.change(width, { target: { value: '6' } });
    fireEvent.keyDown(width, { key: 'Enter' });
    expect(roomSummary(useStore.getState().walls, ids).box!.width).toBe(6 * PIXELS_PER_METRE);

    const x = document.querySelector('input[name="roomX"]') as HTMLInputElement;
    fireEvent.change(x, { target: { value: '4' } });
    fireEvent.blur(x);
    expect(roomSummary(useStore.getState().walls, ids).box!.x).toBe(4 * PIXELS_PER_METRE);
    expect(useStore.getState().objects[0].x).toBeGreaterThan(4 * PIXELS_PER_METRE);
  });

  it('shows the size in metres rather than in pixels', () => {
    selectRoom();
    render(<PropertyInspector />);
    const width = document.querySelector('input[name="roomWidth"]') as HTMLInputElement;
    const box = roomSummary(useStore.getState().walls, useStore.getState().selectedWallIds).box!;
    expect(width.value).toBe((box.width / PIXELS_PER_METRE).toFixed(2).replace('.', ','));
  });

  it('accepts a comma as the decimal separator, and centimetres with it', () => {
    // It is shown with a comma, so typing back what you are shown has
    // to work - and 3,45 m has to land on 3,45 m, not on the nearest
    // grid cell.
    const ids = selectRoom();
    render(<PropertyInspector />);
    const height = document.querySelector('input[name="roomHeight"]') as HTMLInputElement;
    fireEvent.change(height, { target: { value: '3,45' } });
    fireEvent.keyDown(height, { key: 'Enter' });
    expect(roomSummary(useStore.getState().walls, ids).box!.height).toBeCloseTo(3.45 * PIXELS_PER_METRE, 5);
  });

  it('a single wall offers "Select the whole room", which hands over to the Room panel', () => {
    useStore.getState().addRoomWalls({ x: 160, y: 160, width: 400, height: 240 });
    useStore.getState().selectWalls([useStore.getState().walls[0].id]);
    render(<PropertyInspector />);
    fireEvent.click(screen.getByText('Select the whole room'));
    expect(useStore.getState().selectedWallIds).toHaveLength(4);
    expect(document.querySelector('[data-inspector="room"]')).not.toBeNull();
  });
});
