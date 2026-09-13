/** @vitest-environment jsdom */
// feat/editing-and-signal-panel, follow-up task: "podlaczyc istniejacy
// element panelu sygnalizacyjnego do interfejsu". The class of bug this
// suite guards: an element fully implemented in the store/resolver/
// Properties layer but with nothing a user can actually click to place
// it on the canvas. Renders the REAL component against the REAL store
// (no mocking) and clicks it.
//
// feat/synoptic-library: the four screen panels (meter, signal panel,
// group command button, setpoint panel) are entries of the Object
// Library now - under "Control & SCADA screen" - clicked or dragged like
// any symbol. The regression guarded is the same: every inserted element
// must be reachable.
//
// Deliberately NOT a Konva/canvas-rendering test - the library has no
// Konva dependency, so this runs in jsdom without a live browser.

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { useStore } from '../store';
import { Toolbox } from '../components/Toolbox';
import { getSymbolsByCategory } from '../symbols/SymbolRegistry';
import { LIBRARY_DOMAIN_ORDER, WIDGET_TYPES } from '../project/LibraryDomains';
import { setLanguage } from '../i18n/tr';

function resetStore() {
  setLanguage('en');
  useStore.setState({
    objects: [], connections: [], meters: [], signalPanels: [], groupCommands: [], setpointPanels: [],
    selectedIds: [], selectedConnectionIds: [], selectedMeterIds: [], selectedSignalPanelIds: [],
    selectedGroupCommandIds: [], selectedSetpointPanelIds: [],
    clipboard: [], clipboardMeters: [], clipboardSignalPanels: [], clipboardConnections: [],
    history: [{ objects: [], connections: [], meters: [], signalPanels: [], frames: [] }],
    historyIndex: 0,
    screenContents: {},
    recentSymbols: [],
    workMode: 'ROOMS',
  });
}

const entry = (type: string) => document.querySelector(`.library-item[data-type="${type}"]`) as HTMLElement | null;

describe('screen panels - every inserted element (meter, signal panel, ...) is reachable from the library', () => {
  beforeEach(resetStore);
  afterEach(cleanup);

  it('lists all four panels in the library, named', () => {
    render(<Toolbox />);
    expect(WIDGET_TYPES.map(type => entry(type)?.textContent?.trim())).toEqual([
      '▣ Meter panel', '▣ Signal panel', '▣ Group command button', '▣ Setpoint panel',
    ]);
  });

  it('clicking "Meter panel" actually places a meter, selects it and switches to the SYMBOLS mode where it can be moved', () => {
    render(<Toolbox />);
    fireEvent.click(entry('widget.meter')!);
    const state = useStore.getState();
    expect(state.meters.length).toBe(1);
    expect(state.selectedMeterIds).toEqual([state.meters[0].id]);
    expect(state.workMode).toBe('SYMBOLS');
  });

  it('clicking "Signal panel" places and selects a signal panel - the exact bug this suite was written for', () => {
    render(<Toolbox />);
    fireEvent.click(entry('widget.signal_panel')!);
    const state = useStore.getState();
    expect(state.signalPanels.length).toBe(1);
    expect(state.selectedSignalPanelIds).toEqual([state.signalPanels[0].id]);
  });

  it('clicking the group command button and the setpoint panel entries places each of them', () => {
    render(<Toolbox />);
    fireEvent.click(entry('widget.group_command')!);
    fireEvent.click(entry('widget.setpoint_panel')!);
    const state = useStore.getState();
    expect(state.groupCommands.length).toBe(1);
    expect(state.setpointPanels.length).toBe(1);
    expect(state.selectedSetpointPanelIds).toEqual([state.setpointPanels[0].id]);
  });

  it('a placed panel is remembered as recently used, like a dropped symbol', () => {
    render(<Toolbox />);
    fireEvent.click(entry('widget.meter')!);
    expect(useStore.getState().recentSymbols[0]).toBe('widget.meter');
  });
});

describe('Toolbox (Object Library) - every visible symbol in the registry is actually listed to drag', () => {
  beforeEach(resetStore);
  afterEach(cleanup);

  it('lists exactly the symbols the registry considers visible, one draggable entry per symbol, nothing to click open first', () => {
    render(<Toolbox />);
    const expected = Object.values(getSymbolsByCategory()).flat();
    const rendered = screen.getAllByText(/^📄 /);
    expect(rendered.length).toBe(expected.length);
    const renderedLabels = rendered.map(el => el.textContent?.replace('📄 ', '')).sort();
    const expectedLabels = expected.map(def => def.label).sort();
    expect(renderedLabels).toEqual(expectedLabels);
    expect(rendered.every(el => el.getAttribute('draggable') === 'true')).toBe(true);
  });

  // 16. every Object Library group is expanded by default
  it('every domain folder starts expanded - no collapsed folder icon anywhere on first render', () => {
    render(<Toolbox />);
    expect(screen.queryByText('📁')).toBeNull();
    expect(screen.getAllByText('📂').length).toBe(LIBRARY_DOMAIN_ORDER.length);
  });

  it('every SCADA-category symbol expected to be visible right now is listed (Label Frame, Indicator Diode, Meter (SCADA), Boundary Point, Text box) - and no more, no less', () => {
    const scadaItems = getSymbolsByCategory().SCADA || [];
    expect(scadaItems.map(d => d.label).sort()).toEqual(['Boundary Point', 'Indicator Diode', 'Label Frame', 'Meter (SCADA)', 'Text box']);
    render(<Toolbox />);
    for (const def of scadaItems) {
      expect(entry(def.type), def.type).not.toBeNull();
    }
  });
});
