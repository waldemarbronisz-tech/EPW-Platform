// feat/control-elements commit 2 - the group command button: a
// freely-configurable screen element (label + CLOSE/OPEN command + a
// list of member devices) that re-issues one existing SWITCHED command
// to every member at once. Covers the pure resolver logic
// (GroupCommandResolver.ts) and its store wiring (add/update/delete,
// selection, clipboard) - the same split every other element in this
// project's test suite already uses (see group-move-and-shift-select.test.ts
// for the store-side convention, selector-device.test.ts for this
// session's own precedent on a freshly added element/behavior).

import { describe, it, expect, beforeEach } from 'vitest';
import { useStore } from '../store';
import {
  getCommandableDevices, resolveGroupCommandMembers,
  getGroupCommandDanglingMembers, getGroupCommandTargetNames
} from '../elements/GroupCommandResolver';
import { clampGroupCommandWidth, GROUP_COMMAND_MIN_WIDTH, GROUP_COMMAND_MAX_WIDTH, computeGroupCommandHeight } from '../elements/GroupCommandElement';
import type { GroupCommandElement } from '../elements/GroupCommandElement';
import type { Device, SwitchedDevice, SignalDevice } from '../project/DeviceSchema';

function makeSwitched(id: string, designation: string): SwitchedDevice {
  return {
    id, designation, name: 'Wentylator', behavior: 'SWITCHED', kind: 'fan', publishToHa: false,
    feedback: { mode: 'NONE' },
    command: { outputCount: 1, style: 'MAINTAINED', doClose: `ADA1.DO.${designation.length}` },
    supervision: { confirmTimeoutMs: 1000, discrepancyAlarm: false },
    safeState: { onStartup: 'NO_CHANGE', onLinkLoss: 'NO_CHANGE' },
    switchCounter: false
  };
}

function makeSignal(id: string): SignalDevice {
  return {
    id, designation: '-S1', name: 'Czujnik', behavior: 'SIGNAL', kind: 'sensor', publishToHa: false,
    feedback: { di: 'ELA1.DI.1', invert: false }, alarmState: 'HIGH', debounceMs: 50
  };
}

function makeGroupCommand(overrides: Partial<GroupCommandElement> = {}): GroupCommandElement {
  return { id: 'g1', x: 0, y: 0, width: 160, label: 'Start wentylatorow', command: 'CLOSE', deviceIds: [], ...overrides };
}

describe('GroupCommandElement geometry', () => {
  it('clampGroupCommandWidth keeps a width within [min, max]', () => {
    expect(clampGroupCommandWidth(10)).toBe(GROUP_COMMAND_MIN_WIDTH);
    expect(clampGroupCommandWidth(10000)).toBe(GROUP_COMMAND_MAX_WIDTH);
    expect(clampGroupCommandWidth(150)).toBe(150);
  });

  it('computeGroupCommandHeight returns a fixed, positive height', () => {
    expect(computeGroupCommandHeight()).toBeGreaterThan(0);
  });
});

describe('GroupCommandResolver - which devices can be members', () => {
  it('getCommandableDevices keeps only SWITCHED devices', () => {
    const devices: Device[] = [makeSwitched('KOT_W1', '-M1'), makeSignal('KOT_S1')];
    const commandable = getCommandableDevices(devices);
    expect(commandable.map(d => d.id)).toEqual(['KOT_W1']);
  });
});

describe('GroupCommandResolver - resolving members', () => {
  it('resolves a valid SWITCHED member to its designation, not dangling', () => {
    const devices: Device[] = [makeSwitched('KOT_W1', '-M1')];
    const el = makeGroupCommand({ deviceIds: ['KOT_W1'] });
    const members = resolveGroupCommandMembers(el, devices);
    expect(members).toEqual([{ deviceId: 'KOT_W1', designation: '-M1', dangling: false }]);
  });

  it('a member id that does not exist at all is dangling', () => {
    const el = makeGroupCommand({ deviceIds: ['KOT_GONE'] });
    const members = resolveGroupCommandMembers(el, []);
    expect(members[0].dangling).toBe(true);
  });

  it('a member id that exists but is not SWITCHED (behavior changed away) is dangling', () => {
    const devices: Device[] = [makeSignal('KOT_S1')];
    const el = makeGroupCommand({ deviceIds: ['KOT_S1'] });
    const members = resolveGroupCommandMembers(el, devices);
    expect(members[0].dangling).toBe(true);
  });

  it('preserves member order, exactly as stored', () => {
    const devices: Device[] = [makeSwitched('KOT_W1', '-M1'), makeSwitched('KOT_W2', '-M2')];
    const el = makeGroupCommand({ deviceIds: ['KOT_W2', 'KOT_W1'] });
    const members = resolveGroupCommandMembers(el, devices);
    expect(members.map(m => m.deviceId)).toEqual(['KOT_W2', 'KOT_W1']);
  });
});

describe('GroupCommandResolver - dangling member detection', () => {
  it('zero issues for an all-valid member list', () => {
    const devices: Device[] = [makeSwitched('KOT_W1', '-M1')];
    const el = makeGroupCommand({ deviceIds: ['KOT_W1'] });
    expect(getGroupCommandDanglingMembers(el, devices)).toEqual([]);
  });

  it('reports exactly the dangling ones, not the valid ones alongside them', () => {
    const devices: Device[] = [makeSwitched('KOT_W1', '-M1')];
    const el = makeGroupCommand({ deviceIds: ['KOT_W1', 'KOT_GONE'] });
    const issues = getGroupCommandDanglingMembers(el, devices);
    expect(issues).toEqual([{ deviceId: 'KOT_GONE' }]);
  });
});

describe('GroupCommandResolver - what a click would command', () => {
  it('CLOSE targets every valid member\'s own .CLOSE point name', () => {
    const devices: Device[] = [makeSwitched('KOT_W1', '-M1'), makeSwitched('KOT_W2', '-M2')];
    const el = makeGroupCommand({ command: 'CLOSE', deviceIds: ['KOT_W1', 'KOT_W2'] });
    expect(getGroupCommandTargetNames(el, devices).sort()).toEqual(['KOT_W1.CLOSE', 'KOT_W2.CLOSE']);
  });

  it('OPEN targets .OPEN instead of .CLOSE', () => {
    const devices: Device[] = [makeSwitched('KOT_W1', '-M1')];
    const el = makeGroupCommand({ command: 'OPEN', deviceIds: ['KOT_W1'] });
    expect(getGroupCommandTargetNames(el, devices)).toEqual(['KOT_W1.OPEN']);
  });

  it('a dangling member contributes no target name at all', () => {
    const el = makeGroupCommand({ command: 'CLOSE', deviceIds: ['KOT_GONE'] });
    expect(getGroupCommandTargetNames(el, [])).toEqual([]);
  });

  it('an empty member list targets nothing', () => {
    const devices: Device[] = [makeSwitched('KOT_W1', '-M1')];
    const el = makeGroupCommand({ deviceIds: [] });
    expect(getGroupCommandTargetNames(el, devices)).toEqual([]);
  });
});

// ---- Store wiring: CRUD, selection, clipboard, delete ----

function resetStore() {
  useStore.setState({
    objects: [], connections: [], meters: [], signalPanels: [], frames: [], groupCommands: [],
    selectedIds: [], selectedConnectionIds: [], selectedMeterIds: [], selectedSignalPanelIds: [], selectedFrameIds: [], selectedGroupCommandIds: [],
    clipboard: [], clipboardMeters: [], clipboardSignalPanels: [], clipboardFrames: [], clipboardGroupCommands: [], clipboardConnections: [],
    history: [{ objects: [], connections: [], meters: [], signalPanels: [], frames: [], groupCommands: [] }],
    historyIndex: 0
  });
}

describe('Store wiring for groupCommands', () => {
  beforeEach(resetStore);

  it('addGroupCommand assigns a fresh id and appends to the array', () => {
    useStore.getState().addGroupCommand({ x: 10, y: 20, width: 160, label: 'Test', command: 'CLOSE', deviceIds: [] });
    const list = useStore.getState().groupCommands;
    expect(list.length).toBe(1);
    expect(list[0].id).toBeTruthy();
    expect(list[0].label).toBe('Test');
  });

  it('updateGroupCommand merges partial updates without touching other fields', () => {
    useStore.getState().addGroupCommand({ x: 10, y: 20, width: 160, label: 'Test', command: 'CLOSE', deviceIds: [] });
    const id = useStore.getState().groupCommands[0].id;
    useStore.getState().updateGroupCommand(id, { label: 'Renamed', command: 'OPEN' });
    const updated = useStore.getState().groupCommands[0];
    expect(updated.label).toBe('Renamed');
    expect(updated.command).toBe('OPEN');
    expect(updated.x).toBe(10);
  });

  it('selectGroupCommands replaces the selection and clears every other kind (non-multi)', () => {
    useStore.setState({ selectedIds: ['obj1'] });
    useStore.getState().addGroupCommand({ x: 0, y: 0, width: 160, label: 'A', command: 'CLOSE', deviceIds: [] });
    const id = useStore.getState().groupCommands[0].id;
    useStore.getState().selectGroupCommands([id], false);
    expect(useStore.getState().selectedGroupCommandIds).toEqual([id]);
    expect(useStore.getState().selectedIds).toEqual([]);
  });

  it('deleteObjects removes a group command by id and clears its selection', () => {
    useStore.getState().addGroupCommand({ x: 0, y: 0, width: 160, label: 'A', command: 'CLOSE', deviceIds: [] });
    const id = useStore.getState().groupCommands[0].id;
    useStore.getState().selectGroupCommands([id], false);
    useStore.getState().deleteObjects([], [], [], [], [], [id]);
    expect(useStore.getState().groupCommands).toEqual([]);
    expect(useStore.getState().selectedGroupCommandIds).toEqual([]);
  });

  it('copySelected + paste clones a group command with a fresh id, offset, and re-selects the copy', () => {
    useStore.getState().addGroupCommand({ x: 0, y: 0, width: 160, label: 'A', command: 'CLOSE', deviceIds: ['KOT_W1'] });
    const originalId = useStore.getState().groupCommands[0].id;
    useStore.getState().selectGroupCommands([originalId], false);
    useStore.getState().copySelected();
    useStore.getState().paste();

    const all = useStore.getState().groupCommands;
    expect(all.length).toBe(2);
    const pasted = all.find(g => g.id !== originalId)!;
    expect(pasted.label).toBe('A');
    expect(pasted.deviceIds).toEqual(['KOT_W1']);
    expect(pasted.x).toBeGreaterThan(0); // offset from the original
    expect(useStore.getState().selectedGroupCommandIds).toEqual([pasted.id]);
  });

  it('duplicateGroupCommandInPlace leaves an unselected clone at the exact same position', () => {
    useStore.getState().addGroupCommand({ x: 50, y: 50, width: 160, label: 'A', command: 'CLOSE', deviceIds: [] });
    const originalId = useStore.getState().groupCommands[0].id;
    useStore.getState().duplicateGroupCommandInPlace(originalId);
    const all = useStore.getState().groupCommands;
    expect(all.length).toBe(2);
    const clone = all.find(g => g.id !== originalId)!;
    expect(clone.x).toBe(50);
    expect(clone.y).toBe(50);
  });

  it('undo restores a deleted group command', () => {
    useStore.getState().addGroupCommand({ x: 0, y: 0, width: 160, label: 'A', command: 'CLOSE', deviceIds: [] });
    const id = useStore.getState().groupCommands[0].id;
    useStore.getState().deleteObjects([], [], [], [], [], [id]);
    expect(useStore.getState().groupCommands).toEqual([]);
    useStore.getState().undo();
    expect(useStore.getState().groupCommands.map(g => g.id)).toEqual([id]);
  });
});
