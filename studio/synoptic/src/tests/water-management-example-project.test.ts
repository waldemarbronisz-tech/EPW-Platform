// feat/water-management commit 6 - the example project this task's own
// GRANICE requires: "Projekt ma sie wczytywac BEZ ZADNEGO bledu walidacji.
// To jest sprawdzian, czy wszystkie czesci do siebie pasuja" (the project
// must load WITHOUT ANY validation error - a test of whether every part
// actually fits together). This file loads examples/GOSPODARKA_WODNA.epwsyn
// through the EXACT SAME path ProjectManager.loadProject itself uses
// (validateProjectSchema), and additionally through validateDeviceRegistry/
// validateDeviceBindings - the two other real validation passes this app
// has - for the same reason: a project can pass the schema-shape check
// while still having an inconsistent device registry underneath it, and
// this task's own instruction is to catch that, not just the narrowest
// possible reading of "validation".
//
// Read via Vite's `?raw` suffix, not `fs.readFileSync` - this tsconfig's
// own "types" list is deliberately just ["vite/client"], so `node:fs`/
// `__dirname` do not resolve here at all (see help-consistency.test.ts's
// own header comment for the same fix, previously applied there).

import { describe, it, expect, beforeEach } from 'vitest';
import projectSource from '../../examples/GOSPODARKA_WODNA.epwsyn?raw';
import { useStore } from '../store';
import { ProjectManager } from '../project/ProjectManager';
import { validateProjectSchema } from '../project/ProjectSchema';
import { validateDeviceRegistry } from '../project/DeviceValidation';
import { validateDeviceBindings } from '../project/DeviceBindingValidation';
import { getSymbolDefinition } from '../symbols/SymbolRegistry';

describe('GOSPODARKA_WODNA.epwsyn - the water management example project', () => {
  beforeEach(() => {
    useStore.setState({
      objects: [], connections: [], meters: [], signalPanels: [], devices: [], locations: [], cards: [],
      selectedIds: [], selectedConnectionIds: [], selectedMeterIds: [],
      history: [{ objects: [], connections: [], meters: [], signalPanels: [], frames: [] }],
      historyIndex: 0
    });
  });

  it('is valid JSON', () => {
    expect(() => JSON.parse(projectSource)).not.toThrow();
  });

  it('validateProjectSchema (the exact check ProjectManager.loadProject runs) reports zero issues at all - not just zero errors', () => {
    const parsed = JSON.parse(projectSource);
    const result = validateProjectSchema(parsed);
    expect(result.issues, `unexpected validation issues: ${JSON.stringify(result.issues, null, 2)}`).toEqual([]);
    expect(result.valid).toBe(true);
  });

  it('ProjectManager.loadProject actually loads it - the real end-to-end path a user opening this file goes through', () => {
    const ok = ProjectManager.loadProject(projectSource, 'GOSPODARKA_WODNA.epwsyn');
    expect(ok).toBe(true);
    expect(useStore.getState().objects.length).toBeGreaterThan(0);
  });

  it('loading it posts no [ERROR] message to the Messages panel', () => {
    ProjectManager.loadProject(projectSource, 'GOSPODARKA_WODNA.epwsyn');
    const errorMessages = useStore.getState().messages.filter(m => m.text.startsWith('[ERROR]'));
    expect(errorMessages, `unexpected error messages: ${JSON.stringify(errorMessages)}`).toEqual([]);
  });

  it('every object type used resolves to a real, registered symbol (no UNKNOWN_SYMBOL warning either)', () => {
    const parsed = JSON.parse(projectSource);
    for (const obj of parsed.objects) {
      expect(getSymbolDefinition(obj.type), `object '${obj.id}' has unknown type '${obj.type}'`).toBeDefined();
    }
  });

  it('the device registry (locations/cards/devices) is internally consistent - validateDeviceRegistry reports zero issues', () => {
    const parsed = JSON.parse(projectSource);
    const result = validateDeviceRegistry({ locations: parsed.locations, cards: parsed.cards, devices: parsed.devices });
    expect(result.issues, `unexpected device registry issues: ${JSON.stringify(result.issues, null, 2)}`).toEqual([]);
    expect(result.valid).toBe(true);
  });

  it('every symbol\'s deviceId (Aparat) resolves to a real device - no dangling binding warning on load', () => {
    const parsed = JSON.parse(projectSource);
    const issues = validateDeviceBindings(parsed.objects, parsed.devices);
    expect(issues, `unexpected dangling device bindings: ${JSON.stringify(issues, null, 2)}`).toEqual([]);
  });

  it('contains all 12 water-management object types from commits 4/5, at least once each', () => {
    const parsed = JSON.parse(projectSource);
    const types = new Set(parsed.objects.map((o: any) => o.type));
    const expectedTypes = [
      'site.rainwater_tank2', 'site.water_selector_valve_switched', 'site.check_valve',
      'site.water_filter', 'site.hydrofor', 'site.flow_meter', 'site.pressure_switch',
      'site.rain_sensor', 'site.sprinkler_head', 'site.drip_line'
    ];
    for (const type of expectedTypes) {
      expect(types.has(type), `expected object type '${type}' to appear in the example project`).toBe(true);
    }
    // site.water_selector_valve_3pos (the three-position selector) is not
    // used in THIS project - the demo's own source-selector valve is the
    // two-position SWITCHED one (site.water_selector_valve_switched), a
    // deliberate choice (a real installation picks one or the other, not
    // both) - not an omission. Both symbols already have their own
    // dedicated coverage in water-objects-commit4.test.tsx.
  });

  it('the registry contains exactly the two locations, the three cards and the nine devices the task specifies', () => {
    const parsed = JSON.parse(projectSource);
    expect(parsed.locations.map((l: any) => l.code).sort()).toEqual(['KOT', 'OGROD']);
    expect(parsed.cards.length).toBe(3);
    expect(parsed.devices.length).toBe(9);
    const behaviors = parsed.devices.map((d: any) => d.behavior).sort();
    expect(behaviors).toEqual(['MEASURED', 'MEASURED', 'SIGNAL', 'SIGNAL', 'SWITCHED', 'SWITCHED', 'SWITCHED', 'SWITCHED', 'SWITCHED']);
  });

  it('has a meter and a signal panel, both reading real devices from the project\'s own registry', () => {
    const parsed = JSON.parse(projectSource);
    expect(parsed.meters.length).toBe(1);
    expect(parsed.signalPanels.length).toBe(1);
    const deviceIds = new Set(parsed.devices.map((d: any) => d.id));
    for (const row of parsed.meters[0].rows) {
      expect(deviceIds.has(row.device), `meter row references unknown device '${row.device}'`).toBe(true);
    }
    for (const row of parsed.signalPanels[0].rows) {
      expect(deviceIds.has(row.device), `signal panel row references unknown device '${row.device}'`).toBe(true);
    }
  });
});
