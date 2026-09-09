import { describe, it, expect } from 'vitest';
import { validateProjectV2 } from '../project/ProjectV2Validation';

/** Same minimal-project fixture as project-v2-structure.test.ts. */
function makeMinimalProject(): any {
  return {
    format: 'EPW_PROJECT',
    schema_version: 2,
    project: {
      name: 'Test Project',
      description: '',
      created_at: '2026-01-01T00:00:00.000Z',
      modified_at: '2026-01-01T00:00:00.000Z'
    },
    controller: { id: 'PLC1', name: 'Main PLC', hardware: 'EPW Core' },
    symbolLibrary: 'default',
    devices: {
      locations: [{ code: 'KOT', description: 'Kotlownia' }],
      cards: [
        { id: 'ELA1', model: 'ELA01', channelKind: 'DI', channelCount: 64 },
        { id: 'ADA1', model: 'ADA01', channelKind: 'DO', channelCount: 60 }
      ],
      devices: [
        {
          id: 'KOT_KMG1',
          designation: '-K1',
          name: 'Stycznik grzalki',
          behavior: 'SWITCHED',
          kind: 'contactor',
          publishToHa: false,
          feedback: { mode: 'DUAL', diClosed: 'ELA1.DI.1', diOpen: 'ELA1.DI.2' },
          command: { outputCount: 2, style: 'PULSE', doClose: 'ADA1.DO.1', doOpen: 'ADA1.DO.2', pulseMs: 500 },
          supervision: { confirmTimeoutMs: 2000, discrepancyAlarm: true },
          safeState: { onStartup: 'NO_CHANGE', onLinkLoss: 'NO_CHANGE' },
          switchCounter: false
        }
      ]
    },
    screens: [
      {
        id: 'MAIN',
        name: 'Main View',
        isMain: true,
        canvas: { width: 1920, height: 1080, background: '#ffffff', gridSize: 20 },
        backdrop: [],
        items: [],
        connections: [],
        navigation: []
      }
    ]
  };
}

function makeScreenItem(id: string, overrides: any = {}): any {
  return {
    id,
    symbol: 'electrical.contactor',
    x: 100,
    y: 100,
    rotation: 0,
    label: { showDesignation: true, showName: false, position: 'BOTTOM' },
    ...overrides
  };
}

function makeSecondScreen(overrides: any = {}): any {
  return {
    id: 'SECOND',
    name: 'Second Screen',
    isMain: false,
    canvas: { width: 1920, height: 1080, background: '#ffffff', gridSize: 20 },
    backdrop: [],
    items: [],
    connections: [],
    navigation: [],
    ...overrides
  };
}

describe('Project v2 cross-references (validateProjectV2)', () => {
  it('32. a screen item pointing at an existing device is valid', () => {
    const project = makeMinimalProject();
    project.screens[0].items.push(makeScreenItem('ITEM1', { device: 'KOT_KMG1' }));
    expect(validateProjectV2(project).valid).toBe(true);
  });

  it('33. a screen item pointing at a nonexistent device is an error', () => {
    const project = makeMinimalProject();
    project.screens[0].items.push(makeScreenItem('ITEM1', { device: 'KOT_GHOST' }));
    expect(validateProjectV2(project).valid).toBe(false);
  });

  it('34. a screen item without a device field (pure graphics) is valid', () => {
    const project = makeMinimalProject();
    project.screens[0].items.push(makeScreenItem('ITEM1', { symbol: 'graphics.label' }));
    expect(validateProjectV2(project).valid).toBe(true);
  });

  it('35. the same device on two different screens is valid - this is the point of the architecture', () => {
    const project = makeMinimalProject();
    project.screens[0].items.push(makeScreenItem('ITEM1', { device: 'KOT_KMG1' }));
    project.screens.push(makeSecondScreen({ items: [makeScreenItem('ITEM2', { device: 'KOT_KMG1' })] }));

    const result = validateProjectV2(project);
    expect(result.valid).toBe(true);
    expect(result.issues).toEqual([]);
  });

  it('36. a device that appears on no screen at all is valid', () => {
    const project = makeMinimalProject();
    // KOT_KMG1 exists in the device registry; no screen item references it.
    const result = validateProjectV2(project);
    expect(result.valid).toBe(true);
    expect(result.issues).toEqual([]);
  });

  it('37. two items with the same id on one screen is an error', () => {
    const project = makeMinimalProject();
    project.screens[0].items.push(makeScreenItem('ITEM1'), makeScreenItem('ITEM1', { x: 200 }));
    expect(validateProjectV2(project).valid).toBe(false);
  });

  it('38. two items with the same id on different screens is valid', () => {
    const project = makeMinimalProject();
    project.screens[0].items.push(makeScreenItem('ITEM1'));
    project.screens.push(makeSecondScreen({ items: [makeScreenItem('ITEM1')] }));
    expect(validateProjectV2(project).valid).toBe(true);
  });

  it('39. an item with an empty symbol field is an error', () => {
    const project = makeMinimalProject();
    project.screens[0].items.push(makeScreenItem('ITEM1', { symbol: '' }));
    expect(validateProjectV2(project).valid).toBe(false);
  });

  it('40. a connection pointing at a nonexistent item is an error', () => {
    const project = makeMinimalProject();
    project.screens[0].items.push(makeScreenItem('ITEM1'));
    project.screens[0].connections.push({ id: 'C1', fromItem: 'ITEM1', fromPort: 'OUT', toItem: 'GHOST', toPort: 'IN', type: 'electrical_ac' });
    expect(validateProjectV2(project).valid).toBe(false);
  });

  it('41. a connection between items on two different screens is an error', () => {
    const project = makeMinimalProject();
    project.screens[0].items.push(makeScreenItem('ITEM1'));
    project.screens.push(makeSecondScreen({ items: [makeScreenItem('ITEM2')] }));
    // Declared on screen 1, but toItem only exists on screen 2.
    project.screens[0].connections.push({ id: 'C1', fromItem: 'ITEM1', fromPort: 'OUT', toItem: 'ITEM2', toPort: 'IN', type: 'electrical_ac' });
    expect(validateProjectV2(project).valid).toBe(false);
  });

  it('42. a connection from an item to itself is an error', () => {
    const project = makeMinimalProject();
    project.screens[0].items.push(makeScreenItem('ITEM1'));
    project.screens[0].connections.push({ id: 'C1', fromItem: 'ITEM1', fromPort: 'OUT', toItem: 'ITEM1', toPort: 'IN', type: 'electrical_ac' });
    expect(validateProjectV2(project).valid).toBe(false);
  });

  it('43. a navigation link to an existing screen is valid', () => {
    const project = makeMinimalProject();
    project.screens.push(makeSecondScreen());
    project.screens[0].navigation.push({ id: 'NAV1', x: 0, y: 0, label: '-> Second', targetScreen: 'SECOND' });
    expect(validateProjectV2(project).valid).toBe(true);
  });

  it('44. a navigation link to a nonexistent screen is an error', () => {
    const project = makeMinimalProject();
    project.screens[0].navigation.push({ id: 'NAV1', x: 0, y: 0, label: '-> Ghost', targetScreen: 'GHOST' });
    expect(validateProjectV2(project).valid).toBe(false);
  });

  it('45. a navigation link targeting its own screen is an error', () => {
    const project = makeMinimalProject();
    project.screens[0].navigation.push({ id: 'NAV1', x: 0, y: 0, label: '-> Self', targetScreen: 'MAIN' });
    expect(validateProjectV2(project).valid).toBe(false);
  });

  it('46. a navigation link with an empty label is an error', () => {
    const project = makeMinimalProject();
    project.screens.push(makeSecondScreen());
    project.screens[0].navigation.push({ id: 'NAV1', x: 0, y: 0, label: '', targetScreen: 'SECOND' });
    expect(validateProjectV2(project).valid).toBe(false);
  });

  it('47. a project with a broken device registry (channel collision) reports the error via validateDeviceRegistry', () => {
    const project = makeMinimalProject();
    project.devices.devices.push({
      id: 'KOT_KMG2',
      designation: '-K2',
      name: 'Stycznik 2',
      behavior: 'SIGNAL',
      kind: 'level_switch',
      publishToHa: false,
      feedback: { di: 'ELA1.DI.1', invert: false }, // collides with KOT_KMG1's feedback.diClosed
      alarmState: 'HIGH',
      debounceMs: 50
    });
    const result = validateProjectV2(project);
    expect(result.valid).toBe(false);
    expect(result.issues.some(i => i.code === 'CHANNEL_ADDRESS_COLLISION')).toBe(true);
  });
});
