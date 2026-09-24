// The synoptic push button (owner 2026-09-24: "Przycisk robimy - robota
// synoptyki, ale w logice też chcę bity"): a library symbol that writes
// one of the logic's IN bits from the panel - TOGGLE or PULSE - and
// whose cap follows the bit's live value.
import { describe, it, expect, beforeEach } from 'vitest';

import pushButtonSource from '../symbols/scada/PushButtonSymbol.tsx?raw';
import { PUSH_BUTTON_STATES, PUSH_BUTTON_MODES, DEFAULT_PULSE_MS, getPushButtonCapColor } from '../symbols/scada/PushButtonSymbol';
import { COLOR_RUN, COLOR_BEVEL_LIGHT } from '../theme/ScadaTheme';
import { getSymbolDefinition } from '../symbols/SymbolRegistry';
import { symbolUsesTextField } from '../symbols/SymbolRenderer';
import { domainOfType, libraryEntry } from '../project/LibraryDomains';
import { setLanguage, tr } from '../i18n/tr';
import { liveStatesFor } from '../store/liveSlice';
import { isPushButton, pushButtonBit, pushButtonCommands } from '../store/previewSlice';
import { useStore } from '../store';
import type { SynopticObject } from '../store';

function button(overrides: Partial<SynopticObject> = {}): SynopticObject {
  return {
    id: 'B1', type: 'scada.push_button', category: 'SCADA',
    x: 0, y: 0, rotation: 0, scaleX: 1, scaleY: 1,
    visible: true, locked: false, layer: 1,
    tag: '', description: '', color: '', fill: '', border: '',
    text: 'START', font: 'Tahoma', fontSize: 13, tooltip: '',
    width: 150, height: 150, customProperties: {},
    bindings: { command: { tag: 'M.START' } },
    ...overrides,
  };
}

describe('the symbol', () => {
  it('has the two states, RELEASED by default, and the two modes', () => {
    expect(PUSH_BUTTON_STATES).toEqual(['RELEASED', 'PRESSED']);
    expect(PUSH_BUTTON_MODES).toEqual(['TOGGLE', 'PULSE']);
    expect(DEFAULT_PULSE_MS).toBe(500);
    const def = getSymbolDefinition('scada.push_button');
    expect(def?.allowedStates).toEqual(['RELEASED', 'PRESSED']);
    expect(def?.defaultState).toBe('RELEASED');
    expect(def?.defaultWidth).toBe(150);
    expect(def?.hiddenFromLibrary).toBeFalsy();
  });

  it('shows a pressed cap in the theme green and a released one in the light bevel, from the theme only', () => {
    expect(getPushButtonCapColor('PRESSED')).toBe(COLOR_RUN);
    expect(getPushButtonCapColor('RELEASED')).toBe(COLOR_BEVEL_LIGHT);
    expect(pushButtonSource.match(/#[0-9A-Fa-f]{3,8}\b/g)).toBeNull();
  });

  it('sits in the control-system folder under its Polish and English names, and takes a label text', () => {
    expect(domainOfType('scada.push_button')).toBe('AUTOMATION');
    setLanguage('pl');
    expect(libraryEntry('scada.push_button')?.name).toBe('Przycisk');
    setLanguage('en');
    expect(libraryEntry('scada.push_button')?.name).toBe('Push Button');
    expect(symbolUsesTextField('scada.push_button')).toBe(true);
    for (const language of ['pl', 'en'] as const) {
      setLanguage(language);
      for (const key of ['title', 'bit', 'bit_hint', 'mode', 'toggle', 'pulse', 'pulse_ms', 'no_bit']) {
        expect(tr(`push_button.${key}`)).not.toBe(`push_button.${key}`);
      }
    }
  });
});

describe('what a click writes', () => {
  it('TOGGLE writes the opposite of the live value, FALSE when the bit cannot be read', () => {
    expect(isPushButton(button())).toBe(true);
    expect(pushButtonBit(button())).toBe('M.START');
    expect(pushButtonCommands(button(), {})).toEqual([{ bit: 'M.START', value: true }]);
    expect(pushButtonCommands(button(), { 'M.START': true })).toEqual([{ bit: 'M.START', value: false }]);
    expect(pushButtonCommands(button(), { 'M.START': '1' })).toEqual([{ bit: 'M.START', value: false }]);
    expect(pushButtonCommands(button(), { 'M.START': 0 })).toEqual([{ bit: 'M.START', value: true }]);
  });

  it('PULSE writes TRUE and, pulse_ms later, FALSE - the default when none is set', () => {
    expect(pushButtonCommands(button({ editor: { button_mode: 'PULSE', pulse_ms: 120 } }), {}))
      .toEqual([{ bit: 'M.START', value: true }, { bit: 'M.START', value: false, delay_ms: 120 }]);
    expect(pushButtonCommands(button({ editor: { button_mode: 'PULSE' } }), { 'M.START': true }))
      .toEqual([{ bit: 'M.START', value: true }, { bit: 'M.START', value: false, delay_ms: DEFAULT_PULSE_MS }]);
  });

  it('a button without a bit writes nothing', () => {
    expect(pushButtonBit(button({ bindings: {} }))).toBe('');
    expect(pushButtonCommands(button({ bindings: { command: { tag: '  ' } } }), {})).toEqual([]);
  });
});

describe('the panel preview', () => {
  beforeEach(() => {
    useStore.setState({ objects: [button(), button({ id: 'B2', bindings: {} })], devices: [], liveValues: { 'M.START': false },
      pendingCommands: [] });
  });

  it('queues the write for Studio to relay, and returns it as the command of the click', () => {
    const first = useStore.getState().commandAt('B1');
    expect(first).toEqual({ bit: 'M.START', value: true });
    expect(useStore.getState().pendingCommands).toEqual([{ bit: 'M.START', value: true }]);
    expect(useStore.getState().takeCommands()).toEqual([{ bit: 'M.START', value: true }]);
    expect(useStore.getState().pendingCommands).toEqual([]);
  });

  it('a button without a bit is no command - the click falls through to the ordinary preview handling', () => {
    expect(useStore.getState().commandAt('B2')).toBeNull();
    expect(useStore.getState().pendingCommands).toEqual([]);
  });

  it('the cap follows the bit it writes, not the object\'s plain tag', () => {
    const objects = [button({ tag: 'DI1.DI.1' }), button({ id: 'B2', bindings: {} , tag: 'DI1.DI.1' })];
    expect(liveStatesFor(objects, [], { 'M.START': true, 'DI1.DI.1': false })).toEqual({ B1: 'PRESSED', B2: 'RELEASED' });
    expect(liveStatesFor(objects, [], { 'M.START': false })).toEqual({ B1: 'RELEASED' });
    expect(liveStatesFor([button()], [], {})).toEqual({});
  });
});
