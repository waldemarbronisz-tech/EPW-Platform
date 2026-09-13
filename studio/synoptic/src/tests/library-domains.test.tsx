/** @vitest-environment jsdom */
// feat/synoptic-library: the Object Library is a catalogue of symbols,
// divided by ONE criterion (installation domain), searchable in both
// languages, with what the project already uses on top.

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup, fireEvent } from '@testing-library/react';
import {
  allLibraryEntries, domainOfType, entryMatches, groupLibrary, LIBRARY_DOMAIN_ORDER, libraryEntry, projectSymbolUsage, SYMBOL_DOMAIN,
} from '../project/LibraryDomains';
import { SYMBOL_REGISTRY } from '../symbols/SymbolRegistry';
import { setLanguage, symbolNamesInAllLanguages, tr } from '../i18n/tr';
import { useStore } from '../store';
import type { SynopticObject } from '../store';
import { Toolbox } from '../components/Toolbox';
import en from '../i18n/locales/en.json';
import pl from '../i18n/locales/pl.json';

const visibleTypes = Object.values(SYMBOL_REGISTRY).filter(d => !d.hiddenFromLibrary).map(d => d.type).sort();

const obj = (id: string, type: string): SynopticObject => ({
  id, type, category: 'X', x: 0, y: 0, rotation: 0, scaleX: 1, scaleY: 1,
  visible: true, locked: false, layer: 1, tag: '', description: '',
  color: '', fill: '', border: '', text: '', font: 'Tahoma', fontSize: 13,
  tooltip: '', width: 64, height: 64, customProperties: {},
});

function found(query: string) {
  return allLibraryEntries().filter(e => entryMatches(e, query)).map(e => e.type).sort();
}

beforeEach(() => setLanguage('en'));
afterEach(cleanup);

describe('one criterion: the installation domain', () => {
  it('assigns every symbol the library shows to exactly one domain, and nothing it does not show', () => {
    expect(Object.keys(SYMBOL_DOMAIN).sort()).toEqual(visibleTypes);
    expect(visibleTypes.length).toBe(63);
  });

  it('has no group smaller than four, with these counts', () => {
    const counts = Object.fromEntries(groupLibrary(allLibraryEntries()).map(g => [g.domain, g.entries.length]));
    expect(counts).toEqual({ BUILDING: 11, LIGHTING: 9, ELECTRICAL: 10, WATER: 24, HVAC: 4, AUTOMATION: 9 });
    expect(Math.min(...Object.values(counts))).toBeGreaterThanOrEqual(4);
    expect(Object.keys(counts)).toEqual(LIBRARY_DOMAIN_ORDER);
  });

  it('files sensors where they are looked for - on the pipe, in the room - not under "what kind of thing"', () => {
    expect(SYMBOL_DOMAIN['instrumentation.pressure_sensor']).toBe('WATER');
    expect(SYMBOL_DOMAIN['instrumentation.level_sensor']).toBe('WATER');
    expect(SYMBOL_DOMAIN['instrumentation.leak_sensor']).toBe('WATER');
    expect(SYMBOL_DOMAIN['instrumentation.temperature_sensor']).toBe('HVAC');
    expect(SYMBOL_DOMAIN['instrumentation.humidity_sensor']).toBe('HVAC');
    expect(SYMBOL_DOMAIN['site.alarm_beacon']).toBe('ELECTRICAL');
    expect(LIBRARY_DOMAIN_ORDER).not.toContain('INSTRUMENTATION' as never);
    // A symbol hidden from the library still gets a domain for an old project.
    expect(domainOfType('measurements.voltage_display')).toBe('AUTOMATION');
  });
});

describe('names in both languages', () => {
  it('every library entry has an English and a Polish name, and every domain a name in both', () => {
    for (const type of visibleTypes) {
      expect((en.symbol as Record<string, string>)[type], `en ${type}`).toBeTruthy();
      expect((pl.symbol as Record<string, string>)[type], `pl ${type}`).toBeTruthy();
    }
    for (const domain of LIBRARY_DOMAIN_ORDER) {
      expect(tr(`domain.${domain}`, undefined, 'en')).not.toBe(`domain.${domain}`);
      expect(tr(`domain.${domain}`, undefined, 'pl')).not.toBe(`domain.${domain}`);
    }
    const polishFolders = groupLibrary(allLibraryEntries('pl'), '', 'pl').map(g => tr(`domain.${g.domain}`, undefined, 'pl'));
    expect(polishFolders).toEqual(['Budynek i teren', 'Oświetlenie', 'Elektryka', 'Woda i kanalizacja', 'Ogrzewanie i wentylacja', 'Sterowanie i ekran SCADA']);
    expect(polishFolders).not.toContain('TEREN');
    expect(libraryEntry('water.ball_valve', 'pl')!.name).toBe('Zawór kulowy');
    expect(libraryEntry('water.ball_valve', 'en')!.name).toBe('Ball Valve');
  });
});

describe('search', () => {
  it('"zawór" finds every valve by its Polish name even with the interface in English', () => {
    expect(found('zawór')).toEqual([
      'site.check_valve', 'site.water_selector_valve_3pos', 'site.water_selector_valve_switched',
      'water.ball_valve', 'water.drain_valve', 'water.solenoid_valve',
    ]);
    // Typed without the accent, it still finds them.
    expect(found('zawor')).toEqual(found('zawór'));
  });

  it('matches the English name and the type as well', () => {
    expect(found('solenoid')).toEqual(['water.solenoid_valve']);
    expect(found('site.hydrofor')).toEqual(['site.hydrofor']);
    expect(found('hydrofor')).toEqual(['site.hydrofor']);
    expect(found('panel pomiarowy')).toEqual(['widget.meter']);
    expect(symbolNamesInAllLanguages('site.hydrofor')).toEqual(['Pressure Booster', 'Hydrofor']);
  });
});

describe('"In this project"', () => {
  it('counts what is placed on every screen, panels included, most used first', () => {
    const usage = projectSymbolUsage([
      { objects: [obj('a', 'water.pump'), obj('b', 'water.pump'), obj('c', 'building.door')], meters: [{}] },
      { objects: [obj('d', 'water.pump'), obj('e', 'hvac.fan')] },
    ]);
    expect(usage).toEqual([
      { type: 'water.pump', count: 3 },
      { type: 'building.door', count: 1 },
      { type: 'hvac.fan', count: 1 },
      { type: 'widget.meter', count: 1 },
    ]);
  });

  it('is the first folder of the library, the drawing tools are gone from it, and search filters the folders', () => {
    useStore.setState({
      objects: [obj('a', 'water.pump'), obj('b', 'water.pump')],
      meters: [], signalPanels: [], groupCommands: [], setpointPanels: [],
      screenContents: { 'screen-2': { objects: [obj('c', 'hvac.fan')], connections: [], meters: [], signalPanels: [], frames: [], walls: [], groupCommands: [], setpointPanels: [] } },
      activeScreenId: 'screen-1',
      recentSymbols: [],
    });
    render(<Toolbox />);
    const folders = Array.from(document.querySelectorAll('[data-folder]')).map(f => f.getAttribute('data-folder'));
    expect(folders).toEqual(['in-project', 'domain-BUILDING', 'domain-LIGHTING', 'domain-ELECTRICAL', 'domain-WATER', 'domain-HVAC', 'domain-AUTOMATION']);
    const inProject = document.querySelector('[data-folder="in-project"]')!;
    expect(inProject.textContent).toContain('Pump (2)');
    expect(inProject.textContent).toContain('Fan (1)');
    expect(document.body.textContent).not.toContain('Draw wall');
    expect(document.body.textContent).not.toContain('Draw wire');
    expect(document.body.textContent).not.toContain('Illuminance');

    fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'zawór' } });
    const shown = Array.from(document.querySelectorAll('[data-folder^="domain-"] .library-item')).map(i => i.getAttribute('data-type'));
    expect(shown.sort()).toEqual(found('zawór'));
    expect(Array.from(document.querySelectorAll('[data-folder]')).map(f => f.getAttribute('data-folder'))).toEqual(['domain-WATER']);
  });
});
