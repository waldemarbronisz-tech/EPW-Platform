/** @vitest-environment jsdom */
// feat/appearance-selection-frames commit 4: partial Properties
// cleanup, limited to 4b/4c/4d - see PropertyInspector.tsx's own
// comments at each fix for the full reasoning. Renders the REAL
// PropertyInspector against the REAL store (same convention
// toolbar-element-insertion.test.tsx already established for a multi-
// hook component with no dedicated pure logic to test standalone).

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { useStore } from '../store';
import { PropertyInspector } from '../components/PropertyInspector';
import type { SynopticObject } from '../store';

function makeObj(overrides: Partial<SynopticObject> = {}): SynopticObject {
  return {
    id: 'O1', type: 'electrical.circuit_breaker', category: 'Electrical',
    x: 0, y: 0, rotation: 0, scaleX: 1, scaleY: 1,
    visible: true, locked: false, layer: 1,
    tag: 'O1', description: '', color: '#000', fill: '#000', border: '#000',
    text: '', font: 'Arial', fontSize: 12, tooltip: '',
    width: 64, height: 64, customProperties: {},
    ...overrides
  };
}

function resetStore() {
  useStore.setState({
    objects: [], connections: [], meters: [], signalPanels: [], frames: [],
    selectedIds: [], selectedConnectionIds: [], selectedMeterIds: [], selectedSignalPanelIds: [], selectedFrameIds: [],
    history: [{ objects: [], connections: [], meters: [], signalPanels: [], frames: [] }],
    historyIndex: 0
  });
}

describe('Properties - Height field (4b, mandatory test 17)', () => {
  beforeEach(resetStore);
  afterEach(cleanup);

  it('a selected static scada.meter object has no Height field (obj.height is never read for it - see ScadaMeterAdapter)', () => {
    useStore.setState({ objects: [makeObj({ id: 'M1', type: 'scada.meter', width: 160, height: 96 })], selectedIds: ['M1'] });
    render(<PropertyInspector />);
    expect(screen.queryByText('Height')).toBeNull();
  });

  it('a selected dynamic meter (its own Properties branch) has no Height field either', () => {
    useStore.getState().addMeter({ x: 0, y: 0, width: 200, fontSize: 12, rows: [] });
    const id = useStore.getState().meters[0].id;
    useStore.getState().selectMeters([id], false);
    render(<PropertyInspector />);
    expect(screen.queryByText('Height')).toBeNull();
  });

  it('a selected dynamic signal panel has no Height field either', () => {
    useStore.getState().addSignalPanel({ x: 0, y: 0, width: 160, fontSize: 12, rows: [] });
    const id = useStore.getState().signalPanels[0].id;
    useStore.getState().selectSignalPanels([id], false);
    render(<PropertyInspector />);
    expect(screen.queryByText('Height')).toBeNull();
  });

  it('a regular object (not scada.meter) still has a real, working Height field - the hide is type-scoped, not a blanket removal', () => {
    useStore.setState({ objects: [makeObj({ id: 'B1', type: 'electrical.circuit_breaker' })], selectedIds: ['B1'] });
    render(<PropertyInspector />);
    expect(screen.queryByText('Height')).not.toBeNull();
  });
});

describe('Properties - Bindings section (4d, mandatory test 18)', () => {
  beforeEach(resetStore);
  afterEach(cleanup);

  it('a selected static scada.meter object has no Bindings section (it takes data through rows, not tags)', () => {
    useStore.setState({ objects: [makeObj({ id: 'M1', type: 'scada.meter', width: 160, height: 96 })], selectedIds: ['M1'] });
    render(<PropertyInspector />);
    expect(screen.queryByText('Bindings')).toBeNull();
  });

  it('a selected dynamic meter (its own Properties branch) has no Bindings section either', () => {
    useStore.getState().addMeter({ x: 0, y: 0, width: 200, fontSize: 12, rows: [] });
    const id = useStore.getState().meters[0].id;
    useStore.getState().selectMeters([id], false);
    render(<PropertyInspector />);
    expect(screen.queryByText('Bindings')).toBeNull();
  });

  it('a selected dynamic signal panel has no Bindings section either', () => {
    useStore.getState().addSignalPanel({ x: 0, y: 0, width: 160, fontSize: 12, rows: [] });
    const id = useStore.getState().signalPanels[0].id;
    useStore.getState().selectSignalPanels([id], false);
    render(<PropertyInspector />);
    expect(screen.queryByText('Bindings')).toBeNull();
  });

  it('a regular object (not scada.meter) still has its real, working Bindings section - the hide is type-scoped, not a blanket removal', () => {
    useStore.setState({ objects: [makeObj({ id: 'B1', type: 'electrical.circuit_breaker' })], selectedIds: ['B1'] });
    render(<PropertyInspector />);
    expect(screen.queryByText('Bindings')).not.toBeNull();
  });
});

describe('Properties - Text field (4c, not separately numbered but part of the same cleanup)', () => {
  beforeEach(resetStore);
  afterEach(cleanup);

  it('a scada.meter object (dedicated renderer, never reads obj.text) has no Text field', () => {
    useStore.setState({ objects: [makeObj({ id: 'M1', type: 'scada.meter', width: 160, height: 96 })], selectedIds: ['M1'] });
    render(<PropertyInspector />);
    expect(screen.queryByText('Text')).toBeNull();
  });

  it('an indicator lamp (dedicated renderer, never reads obj.text) has no Text field', () => {
    useStore.setState({ objects: [makeObj({ id: 'L1', type: 'electrical.indicator_lamp' })], selectedIds: ['L1'] });
    render(<PropertyInspector />);
    expect(screen.queryByText('Text')).toBeNull();
  });

  it('a standalone graphics.text element (its only reason to exist) still has a working Text field', () => {
    useStore.setState({ objects: [makeObj({ id: 'T1', type: 'graphics.text' })], selectedIds: ['T1'] });
    render(<PropertyInspector />);
    expect(screen.queryByText('Text')).not.toBeNull();
  });
});
