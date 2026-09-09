/** @vitest-environment jsdom */
// feat/editing-and-signal-panel, follow-up task: "podlaczyc istniejacy
// element panelu sygnalizacyjnego do interfejsu". Investigation (see
// raport.md) found the panel's Toolbar button and store wiring already
// present and working against this branch's pushed HEAD - no code
// change was needed. This test is the one explicitly requested
// regardless: a component-level regression test that renders the REAL
// Toolbar against the REAL store (no mocking) and clicks its buttons,
// so the exact class of bug described in the task - an element fully
// implemented in the store/resolver/Properties layer but with no
// button anywhere a user can actually click to place one on the
// canvas - fails loudly here the moment it happens again, for ANY
// toolbar-inserted element (meter or signal panel), not just the one
// that prompted this task.
//
// Deliberately NOT a Konva/canvas-rendering test - Toolbar.tsx itself
// has no Konva dependency, so this runs in jsdom (already a
// devDependency, no new one added) without needing a live browser.

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { useStore } from '../store';
import { Toolbar } from '../components/Toolbar';
import { Toolbox } from '../components/Toolbox';
import { getSymbolsByCategory } from '../symbols/SymbolRegistry';

function resetStore() {
  useStore.setState({
    objects: [], connections: [], meters: [], signalPanels: [],
    selectedIds: [], selectedConnectionIds: [], selectedMeterIds: [], selectedSignalPanelIds: [],
    clipboard: [], clipboardMeters: [], clipboardSignalPanels: [], clipboardConnections: [],
    history: [{ objects: [], connections: [], meters: [], signalPanels: [], frames: [] }],
    historyIndex: 0
  });
}

describe('Toolbar - every toolbar-inserted element (meter, signal panel) is actually reachable from the UI', () => {
  beforeEach(resetStore);
  afterEach(cleanup);

  it('renders a "Dodaj Miernik" button', () => {
    render(<Toolbar />);
    expect(screen.getByTitle('Dodaj Miernik')).toBeTruthy();
  });

  it('renders a "Dodaj Panel Sygnalizacyjny" button - the exact bug this task reported', () => {
    render(<Toolbar />);
    expect(screen.getByTitle('Dodaj Panel Sygnalizacyjny')).toBeTruthy();
  });

  it('clicking "Dodaj Miernik" actually places a meter and selects it', () => {
    render(<Toolbar />);
    fireEvent.click(screen.getByTitle('Dodaj Miernik'));

    const state = useStore.getState();
    expect(state.meters.length).toBe(1);
    expect(state.selectedMeterIds).toEqual([state.meters[0].id]);
  });

  it('clicking "Dodaj Panel Sygnalizacyjny" actually places a signal panel and selects it - the same mechanism as the meter, not a different one', () => {
    render(<Toolbar />);
    fireEvent.click(screen.getByTitle('Dodaj Panel Sygnalizacyjny'));

    const state = useStore.getState();
    expect(state.signalPanels.length).toBe(1);
    expect(state.selectedSignalPanelIds).toEqual([state.signalPanels[0].id]);
  });

  it('both buttons live in the toolbar side by side, so neither can go missing without the other being right there to notice', () => {
    render(<Toolbar />);
    expect(screen.getByTitle('Dodaj Miernik')).toBeTruthy();
    expect(screen.getByTitle('Dodaj Panel Sygnalizacyjny')).toBeTruthy();
  });
});

describe('Toolbox (Object Library) - every visible symbol in the registry is actually listed to drag', () => {
  afterEach(cleanup);

  // The symmetric regression for symbols themselves (as opposed to the
  // meter/panel, which are not symbols at all - see above): a symbol
  // silently flipped to hiddenFromLibrary, or a category the Toolbox
  // fails to enumerate, would strand it exactly the same way the panel
  // was reported stranded, just one layer down. getSymbolsByCategory()
  // is the same "visible" source of truth terminal-centering.test.ts
  // already iterates for a different property (terminal geometry) -
  // this iterates it for reachability instead.
  it('lists exactly the symbols getSymbolsByCategory() considers visible, one .library-item per symbol - every folder already expanded, nothing to click first', () => {
    // feat/appearance-selection-frames commit 4a fixed the discoverability
    // quirk this test used to have to work around (HVAC/Instrumentation
    // started collapsed, so this test used to expand every folder by
    // hand before counting - see mandatory test 16's own dedicated test
    // below for the direct "starts expanded" assertion). No expand step
    // needed here any more: if every folder is already open, this and
    // that test are asserting the same reachability from two angles.
    render(<Toolbox />);

    const expected = Object.values(getSymbolsByCategory()).flat();
    const rendered = screen.getAllByText(/^📄 /);

    expect(rendered.length).toBe(expected.length);
    const renderedLabels = rendered.map(el => el.textContent?.replace('📄 ', '')).sort();
    const expectedLabels = expected.map(def => def.label).sort();
    expect(renderedLabels).toEqual(expectedLabels);
  });

  // 16. every Object Library group is expanded by default
  it('every category starts expanded - no collapsed folder icon anywhere on first render', () => {
    render(<Toolbox />);
    expect(screen.queryByText('📁')).toBeNull();
    // and every category actually rendered as open (📂), not just
    // "no closed icon found because nothing rendered at all"
    const categoryCount = Object.keys(getSymbolsByCategory()).length;
    expect(categoryCount).toBeGreaterThan(0);
    expect(screen.getAllByText('📂').length).toBe(categoryCount);
  });

  it('every SCADA-category symbol expected to be visible right now is listed (Label Frame, Indicator Diode, Meter (SCADA), Boundary Point) - and no more, no less', () => {
    render(<Toolbox />);
    const scadaItems = getSymbolsByCategory().SCADA || [];
    expect(scadaItems.map(d => d.label).sort()).toEqual(['Boundary Point', 'Indicator Diode', 'Label Frame', 'Meter (SCADA)']);
  });
});
