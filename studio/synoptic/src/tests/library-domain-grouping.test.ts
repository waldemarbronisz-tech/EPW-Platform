// fix/hydraulic-connections commit 7 - the 6 mandatory tests for
// regrouping the Object Library by domain instead of when an object was
// first registered. Iterates the real registry (getSymbolsByCategory,
// the same "visible" filter the Toolbox itself uses), not a hand-picked
// list - the same convention site-objects.test.ts/terminal-centering.
// test.ts already established.

import { describe, it, expect } from 'vitest';
import { getSymbolsByCategory, getSymbolDefinition } from '../symbols/SymbolRegistry';

describe('27. TEREN contains exactly five entries', () => {
  it('house, warehouse, sliding gate, grass, concrete road - nothing else', () => {
    const teren = getSymbolsByCategory()['TEREN'] || [];
    expect(teren.map(d => d.type).sort()).toEqual([
      'site.concrete_road', 'site.grass', 'site.house', 'site.sliding_gate', 'site.warehouse'
    ]);
  });
});

describe('28. the rainwater tank is in Water', () => {
  it('site.rainwater_tank2 (the MEASURED water-management tank, DOPLYW/ODPLYW after commit 6) has category Water', () => {
    expect(getSymbolDefinition('site.rainwater_tank2')?.category).toBe('Water');
  });

  it('site.rain_tank (the original site-objects-2d tank, same label) is also in Water - not left behind in TEREN', () => {
    expect(getSymbolDefinition('site.rain_tank')?.category).toBe('Water');
  });
});

describe('29. the alarm beacon is in Electrical', () => {
  it('site.alarm_beacon (Kogut alarmowy) has category Electrical', () => {
    expect(getSymbolDefinition('site.alarm_beacon')?.category).toBe('Electrical');
  });
});

describe('30. the rain sensor is in Instrumentation', () => {
  it('site.rain_sensor (Czujnik deszczu) has category Instrumentation', () => {
    expect(getSymbolDefinition('site.rain_sensor')?.category).toBe('Instrumentation');
  });
});

describe('31. every symbol belongs to EXACTLY one group', () => {
  it('no type appears twice across the combined category listing', () => {
    const allTypes = Object.values(getSymbolsByCategory()).flat().map(d => d.type);
    const uniqueTypes = new Set(allTypes);
    expect(allTypes.length).toBe(uniqueTypes.size);
  });

  it('every relocated object\'s own definition object is a single, unambiguous category - not present under two different registry keys', () => {
    const relocated = [
      'site.rain_tank', 'site.sewage_plant', 'site.water_manhole', 'site.garden_sprinkler', 'site.rainwater_tank2',
      'site.water_selector_valve_switched', 'site.water_selector_valve_3pos', 'site.check_valve', 'site.water_filter',
      'site.hydrofor', 'site.flow_meter', 'site.water_meter', 'site.pressure_switch', 'site.sprinkler_head', 'site.drip_line',
      'site.lamp_post_double', 'site.lamp_post_single', 'site.halogen', 'site.garden_light', 'site.cable_junction',
      'site.alarm_beacon', 'site.alarm_horn', 'site.rain_sensor'
    ];
    const byCategory = getSymbolsByCategory();
    for (const type of relocated) {
      const owners = Object.entries(byCategory).filter(([, defs]) => defs.some(d => d.type === type)).map(([cat]) => cat);
      expect(owners.length, `'${type}' should belong to exactly one category, found in: ${owners.join(', ')}`).toBe(1);
    }
  });
});

describe('32. the total number of visible symbols is unchanged from before the regroup', () => {
  it('51 visible symbols total - a pure category reassignment (no symbol added, removed, or hidden/unhidden) can never change this number', () => {
    const total = Object.values(getSymbolsByCategory()).flat().length;
    expect(total).toBe(51);
  });
});

describe('the library\'s own folder order matches this task\'s own requested sequence', () => {
  it('Electrical, Water, HVAC, Instrumentation, TEREN, SCADA - in exactly that order (Automation has no visible entries today, so its own folder does not appear at all)', () => {
    const order = Object.keys(getSymbolsByCategory());
    expect(order).toEqual(['Electrical', 'Water', 'HVAC', 'Instrumentation', 'TEREN', 'SCADA']);
  });
});

describe('the relocated objects kept their own type string, terminals and states - only category changed (registry-entry move, not a rewrite)', () => {
  it('site.hydrofor: same single WATER terminal, same two states, now category Water', () => {
    const def = getSymbolDefinition('site.hydrofor')!;
    expect(def.category).toBe('Water');
    expect(def.allowedStates).toEqual(['ZALACZONY', 'WYLACZONY']);
    expect(def.terminals).toEqual([{ id: 'WYLOT', side: 'LEFT', medium: 'WATER' }]);
  });

  it('site.cable_junction: same ELECTRICAL terminal, now category Electrical', () => {
    const def = getSymbolDefinition('site.cable_junction')!;
    expect(def.category).toBe('Electrical');
    expect(def.terminals).toEqual([{ id: 'ZASILANIE', side: 'BOTTOM', medium: 'ELECTRICAL' }]);
  });

  it('site.rainwater_tank2: kept its commit-6 DOPLYW/ODPLYW terminals through the move, not reverted to the old single WYLOT', () => {
    const def = getSymbolDefinition('site.rainwater_tank2')!;
    expect(def.terminals).toEqual([
      { id: 'DOPLYW', side: 'LEFT', medium: 'WATER' },
      { id: 'ODPLYW', side: 'RIGHT', medium: 'WATER' }
    ]);
  });
});
