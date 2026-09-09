/** @vitest-environment jsdom */
// feat/help-system commit 2 - the Help window, and mandatory tests
// 7, 8, 11, 12 (test 5/6, search over real body text, are exercised
// further once chapters 1-4 have content - commit 3).

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { useStore } from '../store';
import { HelpWindow } from '../components/HelpWindow';
import { getContextualHelpTopic } from '../help/HelpContextResolver';
import { searchHelp } from '../help/HelpSearch';

function resetStore() {
  useStore.setState({
    objects: [], connections: [], meters: [], signalPanels: [], frames: [],
    selectedIds: [], selectedConnectionIds: [], selectedMeterIds: [], selectedSignalPanelIds: [], selectedFrameIds: [],
    helpLanguage: 'pl',
  });
}

describe('getContextualHelpTopic (mandatory tests 7, 8)', () => {
  beforeEach(resetStore);

  it('test 8: nothing selected opens the introductory topic', () => {
    expect(getContextualHelpTopic(useStore.getState())).toBe('intro-what');
  });

  it('test 7: a selected meter opens the meter topic', () => {
    useStore.setState({ selectedMeterIds: ['M1'] });
    expect(getContextualHelpTopic(useStore.getState())).toBe('elem-meter');
  });

  it('a selected connection opens the wire-drawing topic', () => {
    useStore.setState({ selectedConnectionIds: ['C1'] });
    expect(getContextualHelpTopic(useStore.getState())).toBe('sch-drawing-wire');
  });

  it('a selected signal panel opens the signal panel topic', () => {
    useStore.setState({ selectedSignalPanelIds: ['P1'] });
    expect(getContextualHelpTopic(useStore.getState())).toBe('elem-signal-panel');
  });

  it('a selected boundary-point symbol opens the boundary point element topic', () => {
    useStore.setState({
      selectedIds: ['O1'],
      objects: [{ id: 'O1', type: 'scada.boundary_point', category: 'SCADA', x: 0, y: 0, rotation: 0, scaleX: 1, scaleY: 1, visible: true, locked: false, layer: 1, tag: 'O1', description: '', color: '#000', fill: '#000', border: '#000', text: '', font: 'Tahoma', fontSize: 13, tooltip: '', width: 64, height: 64, customProperties: {} }],
    });
    expect(getContextualHelpTopic(useStore.getState())).toBe('elem-boundary-point');
  });

  it('a selected generic symbol opens the symbol library topic', () => {
    useStore.setState({
      selectedIds: ['O1'],
      objects: [{ id: 'O1', type: 'electrical.circuit_breaker', category: 'Electrical', x: 0, y: 0, rotation: 0, scaleX: 1, scaleY: 1, visible: true, locked: false, layer: 1, tag: 'O1', description: '', color: '#000', fill: '#000', border: '#000', text: '', font: 'Tahoma', fontSize: 13, tooltip: '', width: 64, height: 64, customProperties: {} }],
    });
    expect(getContextualHelpTopic(useStore.getState())).toBe('sym-library');
  });
});

describe('HelpWindow', () => {
  beforeEach(resetStore);
  afterEach(cleanup);

  it('opens on the requested topic and shows its title', () => {
    render(<HelpWindow request={{ topicId: 'intro-what', nonce: 0 }} onClose={() => {}} />);
    expect(screen.getByRole('heading', { name: '1.1 Czym jest EPW-Synoptic-Editor' })).toBeTruthy();
  });

  it('clicking a topic in the contents tree navigates to it', () => {
    render(<HelpWindow request={{ topicId: 'intro-what', nonce: 0 }} onClose={() => {}} />);
    fireEvent.click(screen.getByText('3.1 Lokalizacje'));
    expect(screen.getByRole('heading', { name: '3.1 Lokalizacje' })).toBeTruthy();
  });

  it('test 11: Back and Forward work after visiting three topics', () => {
    render(<HelpWindow request={{ topicId: 'intro-what', nonce: 0 }} onClose={() => {}} />);
    fireEvent.click(screen.getByText('1.2 Miejsce w platformie EPW'));
    fireEvent.click(screen.getByText('1.3 Zasada nadrzedna: ekran informuje, sprzet chroni'));
    // Now on 1.3. Back twice should land on the very first topic (1.1).
    fireEvent.click(screen.getByText('Wstecz'));
    fireEvent.click(screen.getByText('Wstecz'));
    expect(screen.getByRole('heading', { name: '1.1 Czym jest EPW-Synoptic-Editor' })).toBeTruthy();
    fireEvent.click(screen.getByText('Dalej'));
    expect(screen.getByRole('heading', { name: '1.2 Miejsce w platformie EPW' })).toBeTruthy();
    fireEvent.click(screen.getByText('Dalej'));
    expect(screen.getByRole('heading', { name: '1.3 Zasada nadrzedna: ekran informuje, sprzet chroni' })).toBeTruthy();
  });

  it('test 12: switching the help language keeps the current chapter (only its language changes)', () => {
    render(<HelpWindow request={{ topicId: 'reg-locations', nonce: 0 }} onClose={() => {}} />);
    expect(screen.getByRole('heading', { name: '3.1 Lokalizacje' })).toBeTruthy();
    fireEvent.change(screen.getByDisplayValue('Polski'), { target: { value: 'en' } });
    expect(screen.getByRole('heading', { name: '3.1 Locations' })).toBeTruthy();
  });

  it('a repeated request for the same topic (bumped nonce) still re-navigates there', () => {
    const { rerender } = render(<HelpWindow request={{ topicId: 'intro-what', nonce: 0 }} onClose={() => {}} />);
    fireEvent.click(screen.getByText('2.1 Nowy projekt'));
    expect(screen.getByRole('heading', { name: '2.1 Nowy projekt' })).toBeTruthy();
    rerender(<HelpWindow request={{ topicId: 'intro-what', nonce: 1 }} onClose={() => {}} />);
    expect(screen.getByRole('heading', { name: '1.1 Czym jest EPW-Synoptic-Editor' })).toBeTruthy();
  });

  it('the x button calls onClose', () => {
    const onClose = () => { closed = true; };
    let closed = false;
    render(<HelpWindow request={{ topicId: 'intro-what', nonce: 0 }} onClose={onClose} />);
    fireEvent.click(screen.getByTitle('Esc'));
    expect(closed).toBe(true);
  });

  // Escape-closes-help is NOT this component's own responsibility - it
  // is handled by App.tsx's global F1/Escape listener (see that file's
  // own comment for why: an in-browser-only quirk meant a second
  // window-level listener registered from inside this lazily-mounted
  // component never actually fired for the Escape key specifically,
  // despite firing correctly for every other key and despite direct
  // capture/bubble diagnostics on the same target proving nothing else
  // stopped propagation - reusing the already-proven-reliable F1
  // listener sidesteps it entirely). App.tsx itself has no render
  // test in this codebase (react-konva's Canvas does not render in
  // jsdom) - Escape-closes-help is verified empirically in the real
  // browser instead, per this task's own completion report.
});

describe('searchHelp (mandatory test 6)', () => {
  it('an empty query matches nothing', () => {
    expect(searchHelp('', 'pl')).toEqual([]);
    expect(searchHelp('   ', 'pl')).toEqual([]);
  });

  it('test 6: a phrase that matches nothing returns an empty array without throwing', () => {
    expect(() => searchHelp('xyzxyzxyz-nonexistent-phrase', 'pl')).not.toThrow();
    expect(searchHelp('xyzxyzxyz-nonexistent-phrase', 'pl')).toEqual([]);
  });

  it('a phrase from a topic title is found (title-only match, no body content yet)', () => {
    const results = searchHelp('Lokalizacje', 'pl');
    expect(results.some(r => r.topicId === 'reg-locations')).toBe(true);
  });
});
