/** @vitest-environment jsdom */
// Reported from the running editor: "po zmianie materiału ściany nie
// zmienia się na widoku".
//
// It was true, and the reason was not the renderer - that reads
// wall.material and always did. The bar above the canvas only set the
// material for the NEXT wall drawn, so with a finished room selected,
// picking OSB changed a default nobody could see and left the room
// exactly as it was.
//
// Every other bar in this editor that sits above a selection acts on
// it. This one does now too, and these tests hold it there.

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, cleanup, fireEvent } from '@testing-library/react';
import { useStore } from '../store';
import { ModeOptionsBar } from '../components/ModeOptionsBar';
import { setLanguage } from '../i18n/tr';

function room() {
  useStore.getState().addRoomWalls({ x: 160, y: 160, width: 400, height: 240 });
  const ids = useStore.getState().walls.map(w => w.id);
  useStore.getState().selectWalls(ids);
  return ids;
}

function materialSelect() {
  const selects = Array.from(document.querySelectorAll('select')) as HTMLSelectElement[];
  // The wall material is the one offering plaster; the other is the floor.
  return selects.find(s => Array.from(s.options).some(o => o.value === 'tynk'))!;
}

describe('the wall style bar and the selected walls', () => {
  beforeEach(() => {
    setLanguage('en');
    useStore.setState({ walls: [], rooms: [], objects: [], selectedWallIds: [], selectedIds: [], workMode: 'ROOMS' });
  });
  afterEach(cleanup);

  it('changing the material repaints the walls that are selected', () => {
    const ids = room();
    render(<ModeOptionsBar />);

    fireEvent.change(materialSelect(), { target: { value: 'osb' } });

    const walls = useStore.getState().walls.filter(w => ids.includes(w.id));
    expect(walls).toHaveLength(4);
    expect(walls.every(w => w.material === 'osb')).toBe(true);
  });

  it('and still sets what the next wall is drawn with', () => {
    room();
    render(<ModeOptionsBar />);

    fireEvent.change(materialSelect(), { target: { value: 'cegla' } });

    expect(useStore.getState().wallDrawMaterial).toBe('cegla');
  });

  it('with nothing selected it only sets the default, and touches no wall', () => {
    useStore.getState().addRoomWalls({ x: 160, y: 160, width: 400, height: 240 });
    const before = useStore.getState().walls.map(w => w.material);
    useStore.getState().selectWalls([]);
    render(<ModeOptionsBar />);

    fireEvent.change(materialSelect(), { target: { value: 'osb' } });

    expect(useStore.getState().walls.map(w => w.material)).toEqual(before);
    expect(useStore.getState().wallDrawMaterial).toBe('osb');
  });

  it('thickness and height follow the same rule', () => {
    const ids = room();
    render(<ModeOptionsBar />);
    const ranges = Array.from(document.querySelectorAll('input[type="range"]')) as HTMLInputElement[];
    expect(ranges.length).toBeGreaterThanOrEqual(2);

    fireEvent.change(ranges[0], { target: { value: '16' } });
    fireEvent.change(ranges[1], { target: { value: '260' } });

    const walls = useStore.getState().walls.filter(w => ids.includes(w.id));
    expect(walls.every(w => w.thickness === 16)).toBe(true);
    expect(walls.every(w => w.height === 260)).toBe(true);
  });

  it('is one undo, not four', () => {
    const ids = room();
    render(<ModeOptionsBar />);
    fireEvent.change(materialSelect(), { target: { value: 'osb' } });
    expect(useStore.getState().walls.every(w => w.material === 'osb')).toBe(true);

    useStore.getState().undo();

    const walls = useStore.getState().walls.filter(w => ids.includes(w.id));
    expect(walls.some(w => w.material === 'osb')).toBe(false);
  });
});
