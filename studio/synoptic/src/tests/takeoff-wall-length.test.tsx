/** @vitest-environment jsdom */
// Found by drawing a room in the running editor: a room roughly 5 x 5 m
// showed "Wall length 26 cm" in the Quantities panel. The takeoff already
// returns metres; the panel passed that number to formatLength, which
// takes pixels - so every length came out 80 times too small.

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, cleanup } from '@testing-library/react';
import { useStore } from '../store';
import { ProjectManager } from '../project/ProjectManager';
import { TakeoffPanel } from '../components/TakeoffPanel';
import { buildRoomTakeoff } from '../project/RoomTakeoff';
import { m } from '../theme/Scale';

beforeEach(() => {
  ProjectManager.newProject('Takeoff');
});
afterEach(cleanup);

describe('Quantities panel - wall length', () => {
  it('a 4 x 3 m room reads 14,00 m of wall, the same number the takeoff table gives', () => {
    useStore.getState().addRoomWalls({ x: 0, y: 0, width: m(4), height: m(3) });
    const s = useStore.getState();
    const takeoff = buildRoomTakeoff(s.walls, s.objects, s.circuits, s.devices, s.canvasConfig.floorMaterial);
    expect(takeoff.totals.wallLength).toBeCloseTo(14, 5);

    render(<TakeoffPanel />);
    const text = document.body.textContent || '';
    expect(text).toContain('Wall length');
    expect(text).toContain('14,00 m');
    expect(text).not.toContain('18 cm');
  });

  it('two rooms add up, and no wall at all reads zero metres rather than centimetres', () => {
    render(<TakeoffPanel />);
    expect(document.body.textContent).toContain('0,00 m');
    cleanup();
    useStore.getState().addRoomWalls({ x: 0, y: 0, width: m(4), height: m(3) });
    useStore.getState().addRoomWalls({ x: m(6), y: 0, width: m(2), height: m(2) });
    render(<TakeoffPanel />);
    expect(document.body.textContent).toContain('22,00 m');
  });
});
