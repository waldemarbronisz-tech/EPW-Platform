import React, { Suspense, lazy, useState } from 'react';
import { useStore } from '../store';
import { getSymbolDefinition } from '../symbols/SymbolRegistry';
import { symbolUsesTextField } from '../symbols/SymbolRenderer';
import { clampMeterWidth, METER_MIN_WIDTH, METER_MAX_WIDTH, METER_DEFAULT_FONT_SIZE } from '../meter/MeterElement';
import type { MeterElementRow } from '../meter/MeterElement';
import { clampSignalPanelWidth, SIGNAL_PANEL_MIN_WIDTH, SIGNAL_PANEL_MAX_WIDTH, SIGNAL_PANEL_DEFAULT_FONT_SIZE } from '../elements/SignalPanelElement';
import type { SignalPanelRow } from '../elements/SignalPanelElement';
import { clampGroupCommandWidth, GROUP_COMMAND_MIN_WIDTH, GROUP_COMMAND_MAX_WIDTH } from '../elements/GroupCommandElement';
import { getCommandableDevices, resolveGroupCommandMembers, getGroupCommandTargetNames } from '../elements/GroupCommandResolver';
import { clampSetpointWidth, SETPOINT_MIN_WIDTH, SETPOINT_MAX_WIDTH, SETPOINT_DEFAULT_FONT_SIZE } from '../elements/SetpointElement';
import type { SetpointRow } from '../elements/SetpointElement';
import { getSetpointCapableDevices } from '../elements/SetpointResolver';
import { INDICATOR_DIODE_STATES } from '../symbols/scada/IndicatorDiodeSymbol';
import { FONT_SIZE_BASE, FONT_SIZE_SMALL } from '../theme/ScadaTheme';
import type { SynopticConnection, SynopticObject } from '../store';
import { describeObject } from '../utils/ObjectDisplay';
import { resolveNets } from '../project/NetResolver';

// Internal-audit fix: these two wizards are only ever mounted after an
// explicit "+ Wizard" click (see showMeterWizard/showSignalPanelWizard
// below) - lazy-loading them keeps their code out of the initial bundle
// for the (common) session that never opens either one.
const MeterWizardDialog = lazy(() =>
  import('./MeterWizardDialog').then(m => ({ default: m.MeterWizardDialog }))
);
const SignalPanelWizardDialog = lazy(() =>
  import('./SignalPanelWizardDialog').then(m => ({ default: m.SignalPanelWizardDialog }))
);

// feat/appearance-selection-frames commit 1e: every small utility-
// button/annotation size in this file used to be its own literal
// ('10px', '11px', '12px', all slightly different for no reason) -
// now the theme's own FONT_SIZE_SMALL, formatted once here rather
// than re-stringified at each call site.
const UI_SMALL = `${FONT_SIZE_SMALL}px`;

export const PropertyInspector: React.FC = () => {
  const { objects, connections, selectedIds, selectedConnectionIds, updateObject, updateConnection } = useStore();
  const { meters, selectedMeterIds, updateMeter, devices } = useStore();
  const { signalPanels, selectedSignalPanelIds, updateSignalPanel } = useStore();
  const { frames, selectedFrameIds, updateFrame } = useStore();
  const { groupCommands, selectedGroupCommandIds, updateGroupCommand } = useStore();
  const { setpointPanels, selectedSetpointPanelIds, updateSetpointPanel } = useStore();
  // Hooks must run unconditionally on every render (this component is
  // otherwise a chain of early returns depending on what is selected),
  // so this lives up here rather than inside the selectedMeter/
  // selectedSignalPanel branches below, even though each is only ever
  // read by its own branch.
  const [showMeterWizard, setShowMeterWizard] = useState(false);
  const [showSignalPanelWizard, setShowSignalPanelWizard] = useState(false);

  if (selectedIds.length === 0 && selectedConnectionIds.length === 0 && selectedMeterIds.length === 0 && selectedSignalPanelIds.length === 0 && selectedFrameIds.length === 0 && selectedGroupCommandIds.length === 0 && selectedSetpointPanelIds.length === 0) {
    return (
      <div className="property-inspector">
        <div className="inspector-header">Properties</div>
        <div className="inspector-empty">No object selected</div>
      </div>
    );
  }

  const selectionKindCount = (selectedIds.length > 0 ? 1 : 0) + (selectedConnectionIds.length > 0 ? 1 : 0) + (selectedMeterIds.length > 0 ? 1 : 0) + (selectedSignalPanelIds.length > 0 ? 1 : 0) + (selectedFrameIds.length > 0 ? 1 : 0) + (selectedGroupCommandIds.length > 0 ? 1 : 0) + (selectedSetpointPanelIds.length > 0 ? 1 : 0);
  if (selectedIds.length > 1 || selectedConnectionIds.length > 1 || selectedMeterIds.length > 1 || selectedSignalPanelIds.length > 1 || selectedFrameIds.length > 1 || selectedGroupCommandIds.length > 1 || selectedSetpointPanelIds.length > 1 || selectionKindCount > 1) {
    return (
      <div className="property-inspector">
        <div className="inspector-header">Properties</div>
        <div className="inspector-empty">Multiple objects selected</div>
      </div>
    );
  }

  const isConnectionSelected = selectedConnectionIds.length === 1;
  const isMeterSelected = selectedMeterIds.length === 1;
  const isSignalPanelSelected = selectedSignalPanelIds.length === 1;
  const isFrameSelected = selectedFrameIds.length === 1;
  const isGroupCommandSelected = selectedGroupCommandIds.length === 1;
  const isSetpointPanelSelected = selectedSetpointPanelIds.length === 1;
  const selectedObj = isConnectionSelected || isMeterSelected || isSignalPanelSelected || isFrameSelected || isGroupCommandSelected || isSetpointPanelSelected ? null : objects.find(o => o.id === selectedIds[0]);
  const selectedConn = isConnectionSelected ? connections.find(c => c.id === selectedConnectionIds[0]) : null;
  // feat/water-management commit 2: same computed value Canvas.tsx's
  // own render already derives per wire (resolveNets) - resolved only
  // when a connection is actually selected, not on every render.
  const connNetState: 'ACTIVE' | 'INACTIVE' = selectedConn
    ? (resolveNets(connections, objects, devices).find(n => n.connectionIds.includes(selectedConn.id))?.state ?? 'INACTIVE')
    : 'INACTIVE';
  const selectedMeter = isMeterSelected ? meters.find(m => m.id === selectedMeterIds[0]) : null;
  const selectedSignalPanel = isSignalPanelSelected ? signalPanels.find(p => p.id === selectedSignalPanelIds[0]) : null;
  const selectedFrame = isFrameSelected ? frames.find(f => f.id === selectedFrameIds[0]) : null;
  const selectedGroupCommand = isGroupCommandSelected ? groupCommands.find(g => g.id === selectedGroupCommandIds[0]) : null;
  const selectedSetpointPanel = isSetpointPanelSelected ? setpointPanels.find(p => p.id === selectedSetpointPanelIds[0]) : null;

  if (!selectedObj && !selectedConn && !selectedMeter && !selectedSignalPanel && !selectedFrame && !selectedGroupCommand && !selectedSetpointPanel) return null;

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    let finalValue: any = value;

    if (type === 'checkbox') {
      finalValue = (e.target as HTMLInputElement).checked;
    } else if (type === 'number') {
      finalValue = parseFloat(value);
    }

    if (!selectedObj) return;
    if (name.startsWith('editor.')) {
      const [, key] = name.split('.');
      updateObject(selectedObj.id, {
        editor: { ...selectedObj.editor, [key]: finalValue }
      });
    } else if (name.startsWith('bindings.')) {
      const parts = name.split('.');
      const group = parts[1];
      const key = parts[2];

      // Each binding group (state/value/command/alarm/quality) has a
      // slightly different shape (only `command` carries `access`), so
      // TS can't infer a single dynamic-key assignment across all of
      // them - built loosely here, then asserted back to the real
      // `bindings` shape once, at the single point it re-joins typed
      // state, rather than laundering the whole object through `any`.
      const newBindings: Record<string, { tag?: string; data_type?: string; access?: string }> = { ...(selectedObj.bindings || {}) };
      newBindings[group] = {
        ...(newBindings[group] || {}),
        [key]: finalValue
      };

      updateObject(selectedObj.id, { bindings: newBindings as SynopticObject['bindings'] });
    } else {
      updateObject(selectedObj.id, { [name]: finalValue });
    }
  };

  // feat/device-list-ui commit 5: the Aparat dropdown's own handler,
  // separate from the generic handleChange above because assigning a
  // device carries one extra rule ("auto-fills the symbol's label from
  // the device's designation when the symbol's own designation is
  // empty") that no other property on this object has. Only ever fills
  // designation IN - a device is never removed from the label once
  // filled, and an already-set designation is never overwritten.
  const handleDeviceChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    if (!selectedObj) return;
    const deviceId = e.target.value || undefined;
    const device = deviceId ? devices.find(d => d.id === deviceId) : undefined;
    const patch: Partial<SynopticObject> = { deviceId };
    if (device && !selectedObj.designation) {
      patch.designation = device.designation;
    }
    updateObject(selectedObj.id, patch);
    useStore.getState().saveHistory();
  };

  const handleConnChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    if (!selectedConn) return;
    const { name, value } = e.target;
    updateConnection(selectedConn.id, { [name]: value } as Partial<SynopticConnection>);
    useStore.getState().saveHistory();
  };

  const handleCustomPropertyChange = (key: string, value: string) => {
    if (!selectedObj) return;
    updateObject(selectedObj.id, {
      customProperties: {
        ...(selectedObj.customProperties || {}),
        [key]: value
      }
    });
  };

  const addCustomProperty = () => {
    const key = prompt('Enter property name:');
    if (key) {
      handleCustomPropertyChange(key, '');
    }
  };

  // scada.meter row editing: label/value/unit per row, entered by hand
  // for now - wiring this to the device registry is a separate, later
  // task (per the task that added this element).
  const addMeterRow = () => {
    if (!selectedObj) return;
    updateObject(selectedObj.id, {
      meterRows: [...(selectedObj.meterRows || []), { label: '', value: '', unit: '' }]
    });
    useStore.getState().saveHistory();
  };

  const removeMeterRow = (index: number) => {
    if (!selectedObj) return;
    const rows = [...(selectedObj.meterRows || [])];
    rows.splice(index, 1);
    updateObject(selectedObj.id, { meterRows: rows });
    useStore.getState().saveHistory();
  };

  const updateMeterRow = (index: number, field: 'label' | 'value' | 'unit', value: string) => {
    if (!selectedObj) return;
    const rows = (selectedObj.meterRows || []).map((row, i) => i === index ? { ...row, [field]: value } : row);
    updateObject(selectedObj.id, { meterRows: rows });
  };

  if (selectedConn) {
    return (
      <div className="property-inspector">
        <div className="inspector-header">Connection Properties</div>
        <div className="inspector-content">
          <div className="property-group">
            {/* Node-based wiring model: a connection is a freehand
                polyline, not a from/to port pair - there is no source/
                target object or port to show any more. Medium/style/
                state are what a wire actually is now. */}
            <div className="property-group-title">Wire</div>
            <div className="property-row">
              <label>Medium</label>
              <select name="medium" value={selectedConn.medium} onChange={handleConnChange}>
                <option value="ELECTRICAL">Electrical</option>
                <option value="WATER">Water</option>
                <option value="VENTILATION">Ventilation</option>
              </select>
            </div>
            <div className="property-row">
              <label>Style</label>
              <select name="style" value={selectedConn.style} onChange={handleConnChange}>
                <option value="NORMAL">Normal</option>
                <option value="BUS">Bus (busbar / manifold)</option>
              </select>
            </div>
            <div className="property-row">
              {/* feat/water-management commit 2: State used to be a
                  manual dropdown here (mandatory test 17: it no longer
                  is) - a wire's state is now the RESULT of whether its
                  net touches an active source (NetResolver.ts), never
                  a setting. Shown read-only so it is still visible
                  somewhere, computed exactly the same way Canvas.tsx's
                  own render does. */}
              <label>State</label>
              <input type="text" value={connNetState === 'ACTIVE' ? 'Active' : 'Inactive'} disabled />
            </div>
            <div className="property-row">
              <label>Points</label>
              <input type="text" value={selectedConn.points.length} disabled />
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (selectedMeter) {
    // Part A: title/font size/width plus manual row management (add,
    // remove, reorder, edit label/value/unit). Picking a device for a
    // row (the wizard, part C) and everything that resolves a device's
    // own unit/format/preview value (part B) are their own commits -
    // this only manages the row list itself, which any row needs
    // regardless of where it came from.
    const setRows = (rows: MeterElementRow[]) => {
      updateMeter(selectedMeter.id, { rows });
      useStore.getState().saveHistory();
    };
    const addManualRow = () => setRows([...selectedMeter.rows, { device: '', label: '', manualValue: '', manualUnit: '' }]);
    const removeRow = (idx: number) => setRows(selectedMeter.rows.filter((_, i) => i !== idx));
    const moveRow = (idx: number, dir: -1 | 1) => {
      const target = idx + dir;
      if (target < 0 || target >= selectedMeter.rows.length) return;
      const rows = [...selectedMeter.rows];
      [rows[idx], rows[target]] = [rows[target], rows[idx]];
      setRows(rows);
    };
    const updateRowField = (idx: number, field: keyof MeterElementRow, value: string) => {
      setRows(selectedMeter.rows.map((r, i) => i === idx ? { ...r, [field]: value } : r));
    };

    return (
      <>
      <div className="property-inspector">
        <div className="inspector-header">Meter Properties</div>
        <div className="inspector-content">
          <div className="property-group">
            <div className="property-group-title">Meter</div>
            <div className="property-row">
              <label>Title</label>
              <input
                type="text"
                value={selectedMeter.title || ''}
                onChange={(e) => updateMeter(selectedMeter.id, { title: e.target.value })}
                onBlur={() => useStore.getState().saveHistory()}
              />
            </div>
            <div className="property-row">
              <label>Font Size</label>
              <input
                type="number"
                value={selectedMeter.fontSize || METER_DEFAULT_FONT_SIZE}
                onChange={(e) => {
                  const size = parseFloat(e.target.value);
                  if (!isNaN(size) && size > 0) updateMeter(selectedMeter.id, { fontSize: size });
                }}
                onBlur={() => useStore.getState().saveHistory()}
              />
            </div>
            <div className="property-row">
              <label>Width</label>
              <input
                type="number"
                min={METER_MIN_WIDTH}
                max={METER_MAX_WIDTH}
                value={Math.round(selectedMeter.width)}
                onChange={(e) => {
                  const width = parseFloat(e.target.value);
                  if (!isNaN(width)) updateMeter(selectedMeter.id, { width: clampMeterWidth(width) });
                }}
                onBlur={() => useStore.getState().saveHistory()}
              />
            </div>
          </div>

          <div className="property-group">
            <div className="property-group-title">
              Rows
              <button onClick={() => setShowMeterWizard(true)} style={{ marginLeft: 'auto', fontSize: UI_SMALL }}>Kreator...</button>
              <button onClick={addManualRow} style={{ fontSize: UI_SMALL }}>+ Manual row</button>
            </div>
            {selectedMeter.rows.map((row, idx) => (
              <div
                className="property-row"
                key={idx}
                style={{ gap: '2px', alignItems: 'center', cursor: row.device ? 'pointer' : undefined }}
                // feat/device-form-from-canvas commit 2b: double-click on a
                // device-bound row opens that device's own form, through
                // the exact same shared function every other entry point
                // uses - a manual row (no device) has nothing to open.
                onDoubleClick={() => row.device && useStore.getState().openDeviceForm(row.device, 'Meter Row')}
                title={row.device ? "Double-click: open this device's form" : undefined}
              >
                <button onClick={() => moveRow(idx, -1)} disabled={idx === 0} style={{ fontSize: UI_SMALL }}>up</button>
                <button onClick={() => moveRow(idx, 1)} disabled={idx === selectedMeter.rows.length - 1} style={{ fontSize: UI_SMALL }}>down</button>
                <input
                  type="text"
                  placeholder="Label"
                  value={row.label}
                  onChange={(e) => updateRowField(idx, 'label', e.target.value)}
                  onBlur={() => useStore.getState().saveHistory()}
                  style={{ flex: 2 }}
                />
                {!row.device && (
                  <>
                    <input
                      type="text"
                      placeholder="Value"
                      value={row.manualValue}
                      onChange={(e) => updateRowField(idx, 'manualValue', e.target.value)}
                      onBlur={() => useStore.getState().saveHistory()}
                      style={{ flex: 1 }}
                    />
                    <input
                      type="text"
                      placeholder="Unit"
                      value={row.manualUnit}
                      onChange={(e) => updateRowField(idx, 'manualUnit', e.target.value)}
                      onBlur={() => useStore.getState().saveHistory()}
                      style={{ flex: 1 }}
                    />
                  </>
                )}
                {row.device && <span style={{ flex: 2, fontSize: UI_SMALL }}><em>device: {row.device}</em></span>}
                <button onClick={() => removeRow(idx)} style={{ fontSize: UI_SMALL }}>x</button>
              </div>
            ))}
            {selectedMeter.rows.length === 0 && (
              <div className="property-row"><em>No rows yet - use + Manual row to add one.</em></div>
            )}
          </div>
        </div>
      </div>
      {showMeterWizard && (
        <Suspense fallback={null}>
          <MeterWizardDialog
            devices={devices}
            onCancel={() => setShowMeterWizard(false)}
            onAddManualRow={addManualRow}
            onConfirm={(newRows) => {
              setRows([...selectedMeter.rows, ...newRows]);
              setShowMeterWizard(false);
            }}
          />
        </Suspense>
      )}
      </>
    );
  }

  if (selectedSignalPanel) {
    // commit 6: title/font size/width plus manual row management,
    // mirroring the meter's own Part A branch above - see raport.md
    // for what stayed shared (PanelChrome.tsx, PanelLayout.ts) and what
    // is duplicated here (this row-management UI itself: the manual
    // FIELDS differ enough - one text label plus a value/unit pair for
    // the meter, one text label plus a three-way state select here -
    // that a fully generic version would need its own render-prop
    // customization, more indirection than these ~40 lines justify).
    // commit 8: picking a device for a row via the location-grouped
    // wizard, mirroring the meter's own MeterWizardDialog wiring below.
    // Resolving a row from the device list is commit 7's own concern
    // (SignalPanelResolver.ts), already wired into SignalPanelElementNode.
    const setRows = (rows: SignalPanelRow[]) => {
      updateSignalPanel(selectedSignalPanel.id, { rows });
      useStore.getState().saveHistory();
    };
    const addManualRow = () => setRows([...selectedSignalPanel.rows, { device: '', label: '', manualState: 'OFF' }]);
    const removeRow = (idx: number) => setRows(selectedSignalPanel.rows.filter((_, i) => i !== idx));
    const moveRow = (idx: number, dir: -1 | 1) => {
      const target = idx + dir;
      if (target < 0 || target >= selectedSignalPanel.rows.length) return;
      const rows = [...selectedSignalPanel.rows];
      [rows[idx], rows[target]] = [rows[target], rows[idx]];
      setRows(rows);
    };
    const updateRowField = (idx: number, field: keyof SignalPanelRow, value: string) => {
      setRows(selectedSignalPanel.rows.map((r, i) => i === idx ? { ...r, [field]: value } : r));
    };

    return (
      <>
      <div className="property-inspector">
        <div className="inspector-header">Signal Panel Properties</div>
        <div className="inspector-content">
          <div className="property-group">
            <div className="property-group-title">Signal Panel</div>
            <div className="property-row">
              <label>Title</label>
              <input
                type="text"
                value={selectedSignalPanel.title || ''}
                onChange={(e) => updateSignalPanel(selectedSignalPanel.id, { title: e.target.value })}
                onBlur={() => useStore.getState().saveHistory()}
              />
            </div>
            <div className="property-row">
              <label>Font Size</label>
              <input
                type="number"
                value={selectedSignalPanel.fontSize || SIGNAL_PANEL_DEFAULT_FONT_SIZE}
                onChange={(e) => {
                  const size = parseFloat(e.target.value);
                  if (!isNaN(size) && size > 0) updateSignalPanel(selectedSignalPanel.id, { fontSize: size });
                }}
                onBlur={() => useStore.getState().saveHistory()}
              />
            </div>
            <div className="property-row">
              <label>Width</label>
              <input
                type="number"
                min={SIGNAL_PANEL_MIN_WIDTH}
                max={SIGNAL_PANEL_MAX_WIDTH}
                value={Math.round(selectedSignalPanel.width)}
                onChange={(e) => {
                  const width = parseFloat(e.target.value);
                  if (!isNaN(width)) updateSignalPanel(selectedSignalPanel.id, { width: clampSignalPanelWidth(width) });
                }}
                onBlur={() => useStore.getState().saveHistory()}
              />
            </div>
          </div>

          <div className="property-group">
            <div className="property-group-title">
              Rows
              <button onClick={() => setShowSignalPanelWizard(true)} style={{ marginLeft: 'auto', fontSize: UI_SMALL }}>Kreator...</button>
              <button onClick={addManualRow} style={{ fontSize: UI_SMALL }}>+ Manual row</button>
            </div>
            {selectedSignalPanel.rows.map((row, idx) => (
              <div
                className="property-row"
                key={idx}
                style={{ gap: '2px', alignItems: 'center', cursor: row.device ? 'pointer' : undefined }}
                // feat/device-form-from-canvas commit 2c: same shared
                // openDeviceForm the meter row's own double-click uses.
                onDoubleClick={() => row.device && useStore.getState().openDeviceForm(row.device, 'Signal Panel Row')}
                title={row.device ? "Double-click: open this device's form" : undefined}
              >
                <button onClick={() => moveRow(idx, -1)} disabled={idx === 0} style={{ fontSize: UI_SMALL }}>up</button>
                <button onClick={() => moveRow(idx, 1)} disabled={idx === selectedSignalPanel.rows.length - 1} style={{ fontSize: UI_SMALL }}>down</button>
                <input
                  type="text"
                  placeholder="Label"
                  value={row.label}
                  onChange={(e) => updateRowField(idx, 'label', e.target.value)}
                  onBlur={() => useStore.getState().saveHistory()}
                  style={{ flex: 2 }}
                />
                {!row.device && (
                  <select
                    value={row.manualState}
                    onChange={(e) => { updateRowField(idx, 'manualState', e.target.value); useStore.getState().saveHistory(); }}
                    style={{ flex: 1 }}
                  >
                    {INDICATOR_DIODE_STATES.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                )}
                {row.device && <span style={{ flex: 1, fontSize: UI_SMALL }}><em>device: {row.device}</em></span>}
                <button onClick={() => removeRow(idx)} style={{ fontSize: UI_SMALL }}>x</button>
              </div>
            ))}
            {selectedSignalPanel.rows.length === 0 && (
              <div className="property-row"><em>No rows yet - use + Manual row to add one.</em></div>
            )}
          </div>
        </div>
      </div>
      {showSignalPanelWizard && (
        <Suspense fallback={null}>
          <SignalPanelWizardDialog
            devices={devices}
            onCancel={() => setShowSignalPanelWizard(false)}
            onAddManualRow={addManualRow}
            onConfirm={(newRows) => {
              setRows([...selectedSignalPanel.rows, ...newRows]);
              setShowSignalPanelWizard(false);
            }}
          />
        </Suspense>
      )}
      </>
    );
  }

  if (selectedFrame) {
    // commit 3: a frame is pure graphics - no rows, no width/height
    // fields (3a/3f: those are set by dragging it out and resized via
    // its own corner/edge handles, not typed in here). Only title and
    // where it sits in the top edge are editable in Properties; variant
    // (PLAIN/BUILDING) is fixed at creation by which toolbar button
    // drew it, the same way a symbol's own type cannot be changed
    // after the fact from Properties either.
    return (
      <div className="property-inspector">
        <div className="inspector-header">Frame Properties</div>
        <div className="inspector-content">
          <div className="property-group">
            <div className="property-group-title">Frame</div>
            <div className="property-row">
              <label>Variant</label>
              <input type="text" value={selectedFrame.variant} disabled />
            </div>
            <div className="property-row">
              <label>Title</label>
              <input
                type="text"
                value={selectedFrame.title || ''}
                onChange={(e) => updateFrame(selectedFrame.id, { title: e.target.value })}
                onBlur={() => useStore.getState().saveHistory()}
              />
            </div>
            <div className="property-row">
              <label>Title Position</label>
              <select
                value={selectedFrame.titlePosition}
                onChange={(e) => { updateFrame(selectedFrame.id, { titlePosition: e.target.value as typeof selectedFrame.titlePosition }); useStore.getState().saveHistory(); }}
              >
                <option value="TOP_LEFT">Top Left</option>
                <option value="TOP_CENTER">Top Center</option>
              </select>
            </div>
            <div className="property-row">
              <label>Width</label>
              <input type="number" value={Math.round(selectedFrame.width)} disabled />
            </div>
            <div className="property-row">
              <label>Height</label>
              <input type="number" value={Math.round(selectedFrame.height)} disabled />
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (selectedGroupCommand) {
    // feat/control-elements commit 2: label/command/members, freely
    // configurable per this task's own directive ("dowolnie
    // konfigurowac" - works equally for a lighting group or a fan
    // group, not hardcoded to either). Member picking is a plain
    // dropdown-plus-list, not a wizard dialog like the meter/signal
    // panel's own Kreator - a device-id list this short does not
    // justify one. "Testuj (podglad)" never sends anything (this
    // editor is design-time only - see GroupCommandResolver.ts's own
    // header) - it only logs what a click WOULD command, into the
    // existing Messages panel, same honesty convention as the meter/
    // signal panel's own PREVIEW state.
    const commandable = getCommandableDevices(devices);
    const members = resolveGroupCommandMembers(selectedGroupCommand, devices);
    const availableToAdd = commandable.filter(d => !selectedGroupCommand.deviceIds.includes(d.id));

    const setDeviceIds = (deviceIds: string[]) => {
      updateGroupCommand(selectedGroupCommand.id, { deviceIds });
      useStore.getState().saveHistory();
    };
    const addMember = (deviceId: string) => {
      if (!deviceId || selectedGroupCommand.deviceIds.includes(deviceId)) return;
      setDeviceIds([...selectedGroupCommand.deviceIds, deviceId]);
    };
    const removeMember = (deviceId: string) => setDeviceIds(selectedGroupCommand.deviceIds.filter(id => id !== deviceId));

    return (
      <div className="property-inspector">
        <div className="inspector-header">Group Command Properties</div>
        <div className="inspector-content">
          <div className="property-group">
            <div className="property-group-title">Group Command Button</div>
            <div className="property-row">
              <label>Description (label)</label>
              <input
                type="text"
                value={selectedGroupCommand.label}
                onChange={(e) => updateGroupCommand(selectedGroupCommand.id, { label: e.target.value })}
                onBlur={() => useStore.getState().saveHistory()}
                placeholder="e.g. Start fans"
              />
            </div>
            <div className="property-row">
              <label>Command</label>
              <select
                value={selectedGroupCommand.command}
                onChange={(e) => { updateGroupCommand(selectedGroupCommand.id, { command: e.target.value as 'CLOSE' | 'OPEN' }); useStore.getState().saveHistory(); }}
              >
                <option value="CLOSE">CLOSE (on)</option>
                <option value="OPEN">OPEN (off)</option>
              </select>
            </div>
            <div className="property-row">
              <label>Width</label>
              <input
                type="number"
                min={GROUP_COMMAND_MIN_WIDTH}
                max={GROUP_COMMAND_MAX_WIDTH}
                value={Math.round(selectedGroupCommand.width)}
                onChange={(e) => {
                  const width = parseFloat(e.target.value);
                  if (!isNaN(width)) updateGroupCommand(selectedGroupCommand.id, { width: clampGroupCommandWidth(width) });
                }}
                onBlur={() => useStore.getState().saveHistory()}
              />
            </div>
          </div>

          <div className="property-group">
            <div className="property-group-title">
              Devices in Group ({members.length})
              <select
                style={{ marginLeft: 'auto', fontSize: UI_SMALL }}
                value=""
                onChange={(e) => addMember(e.target.value)}
                disabled={availableToAdd.length === 0}
              >
                <option value="">+ Add device...</option>
                {availableToAdd.map(d => <option key={d.id} value={d.id}>{d.id} ({d.designation})</option>)}
              </select>
            </div>
            {members.map(m => (
              <div className="property-row" key={m.deviceId} style={{ gap: '4px', alignItems: 'center' }}>
                <span style={{ flex: 1, fontSize: UI_SMALL }}>
                  {m.deviceId} {m.dangling ? <em>(missing / not SWITCHED)</em> : `(${m.designation})`}
                </span>
                <button onClick={() => removeMember(m.deviceId)} style={{ fontSize: UI_SMALL }}>x</button>
              </div>
            ))}
            {members.length === 0 && (
              <div className="property-row"><em>No devices - use the list above to add one.</em></div>
            )}
          </div>

          <div className="property-group">
            <button
              onClick={() => {
                const names = getGroupCommandTargetNames(selectedGroupCommand, devices);
                useStore.getState().addMessage(
                  names.length > 0
                    ? `[INFO] "${selectedGroupCommand.label || selectedGroupCommand.id}" would send to: ${names.join(', ')}`
                    : `[WARNING] "${selectedGroupCommand.label || selectedGroupCommand.id}" has no valid device to command`
                );
              }}
            >
              Testuj (podglad)
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (selectedSetpointPanel) {
    // feat/selector-symbol-setpoint-alarm: title/font size/width plus
    // row management, mirroring the meter's own Part A branch above -
    // same shape (label + manual value/unit, or a bound device). No
    // wizard dialog here (proportionate to this element's own scope,
    // unlike the meter/signal panel's own location-grouped Kreator) -
    // picking a MODULATED device from the dropdown below adds it as a
    // new row directly, the same pattern the group command button's own
    // member picker already uses.
    const setRows = (rows: SetpointRow[]) => {
      updateSetpointPanel(selectedSetpointPanel.id, { rows });
      useStore.getState().saveHistory();
    };
    const addManualRow = () => setRows([...selectedSetpointPanel.rows, { device: '', label: '', manualValue: '', manualUnit: '' }]);
    const removeRow = (idx: number) => setRows(selectedSetpointPanel.rows.filter((_, i) => i !== idx));
    const moveRow = (idx: number, dir: -1 | 1) => {
      const target = idx + dir;
      if (target < 0 || target >= selectedSetpointPanel.rows.length) return;
      const rows = [...selectedSetpointPanel.rows];
      [rows[idx], rows[target]] = [rows[target], rows[idx]];
      setRows(rows);
    };
    const updateRowField = (idx: number, field: keyof SetpointRow, value: string) => {
      setRows(selectedSetpointPanel.rows.map((r, i) => i === idx ? { ...r, [field]: value } : r));
    };
    const usedDeviceIds = new Set(selectedSetpointPanel.rows.map(r => r.device).filter(Boolean));
    const availableToAdd = getSetpointCapableDevices(devices).filter(d => !usedDeviceIds.has(d.id));
    const addDeviceRow = (deviceId: string) => {
      if (!deviceId) return;
      setRows([...selectedSetpointPanel.rows, { device: deviceId, label: '', manualValue: '', manualUnit: '' }]);
    };

    return (
      <div className="property-inspector">
        <div className="inspector-header">Setpoint Panel Properties</div>
        <div className="inspector-content">
          <div className="property-group">
            <div className="property-group-title">Setpoint Panel</div>
            <div className="property-row">
              <label>Title</label>
              <input
                type="text"
                value={selectedSetpointPanel.title || ''}
                onChange={(e) => updateSetpointPanel(selectedSetpointPanel.id, { title: e.target.value })}
                onBlur={() => useStore.getState().saveHistory()}
              />
            </div>
            <div className="property-row">
              <label>Font Size</label>
              <input
                type="number"
                value={selectedSetpointPanel.fontSize || SETPOINT_DEFAULT_FONT_SIZE}
                onChange={(e) => {
                  const size = parseFloat(e.target.value);
                  if (!isNaN(size) && size > 0) updateSetpointPanel(selectedSetpointPanel.id, { fontSize: size });
                }}
                onBlur={() => useStore.getState().saveHistory()}
              />
            </div>
            <div className="property-row">
              <label>Width</label>
              <input
                type="number"
                min={SETPOINT_MIN_WIDTH}
                max={SETPOINT_MAX_WIDTH}
                value={Math.round(selectedSetpointPanel.width)}
                onChange={(e) => {
                  const width = parseFloat(e.target.value);
                  if (!isNaN(width)) updateSetpointPanel(selectedSetpointPanel.id, { width: clampSetpointWidth(width) });
                }}
                onBlur={() => useStore.getState().saveHistory()}
              />
            </div>
          </div>

          <div className="property-group">
            <div className="property-group-title">
              Rows
              <select
                style={{ marginLeft: 'auto', fontSize: UI_SMALL }}
                value=""
                onChange={(e) => addDeviceRow(e.target.value)}
                disabled={availableToAdd.length === 0}
              >
                <option value="">+ Add device...</option>
                {availableToAdd.map(d => <option key={d.id} value={d.id}>{d.id} ({d.designation})</option>)}
              </select>
              <button onClick={addManualRow} style={{ fontSize: UI_SMALL }}>+ Manual row</button>
            </div>
            {selectedSetpointPanel.rows.map((row, idx) => (
              <div className="property-row" key={idx} style={{ gap: '2px', alignItems: 'center' }}>
                <button onClick={() => moveRow(idx, -1)} disabled={idx === 0} style={{ fontSize: UI_SMALL }}>up</button>
                <button onClick={() => moveRow(idx, 1)} disabled={idx === selectedSetpointPanel.rows.length - 1} style={{ fontSize: UI_SMALL }}>down</button>
                <input
                  type="text"
                  placeholder="Label"
                  value={row.label}
                  onChange={(e) => updateRowField(idx, 'label', e.target.value)}
                  onBlur={() => useStore.getState().saveHistory()}
                  style={{ flex: 2 }}
                />
                {!row.device && (
                  <>
                    <input
                      type="text"
                      placeholder="Value"
                      value={row.manualValue}
                      onChange={(e) => updateRowField(idx, 'manualValue', e.target.value)}
                      onBlur={() => useStore.getState().saveHistory()}
                      style={{ flex: 1 }}
                    />
                    <input
                      type="text"
                      placeholder="Unit"
                      value={row.manualUnit}
                      onChange={(e) => updateRowField(idx, 'manualUnit', e.target.value)}
                      onBlur={() => useStore.getState().saveHistory()}
                      style={{ flex: 1 }}
                    />
                  </>
                )}
                {row.device && <span style={{ flex: 2, fontSize: UI_SMALL }}><em>device: {row.device}</em></span>}
                <button onClick={() => removeRow(idx)} style={{ fontSize: UI_SMALL }}>x</button>
              </div>
            ))}
            {selectedSetpointPanel.rows.length === 0 && (
              <div className="property-row"><em>No rows yet - use + Manual row, or pick a MODULATED device above.</em></div>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Object Property Inspector Below
  if (!selectedObj) return null;

  return (
    <div className="property-inspector">
      <div className="inspector-header">Properties</div>
      <div className="inspector-content">
        <div className="property-group">
          <div className="property-group-title">General</div>

          <div className="property-row">
            <label>Type</label>
            <input type="text" value={selectedObj.type} disabled />
          </div>
          <div className="property-row">
            <label>Designation</label>
            <input
              type="text"
              name="designation"
              value={selectedObj.designation || ''}
              onChange={handleChange}
              onBlur={() => useStore.getState().saveHistory()}
              list={selectedObj.type === 'scada.boundary_point' ? 'boundary-point-labels' : undefined}
            />
            {selectedObj.type === 'scada.boundary_point' && (
              // Ready-made suggestions for a boundary point's label, per
              // its own spec - a suggestion, not a restriction: any text
              // the user types is accepted, this only offers common ones.
              <datalist id="boundary-point-labels">
                <option value="ZKP" />
                <option value="PGE Dystrybucja" />
                <option value="STUDNIA" />
                <option value="DOM" />
                <option value="WARSZTAT" />
                <option value="MAGAZYN" />
                <option value="OGROD" />
                <option value="OCZYSZCZALNIA" />
                <option value="NAWADNIANIE" />
                <option value="CZERPNIA" />
                <option value="WYRZUTNIA" />
                <option value="CENTRALA" />
                <option value="REKUPERATOR" />
              </datalist>
            )}
          </div>
          <div className="property-row">
            <label>Name</label>
            <input type="text" name="name" value={selectedObj.name || ''} onChange={handleChange} onBlur={() => useStore.getState().saveHistory()} />
          </div>
          {/* feat/device-list-ui commit 5: same exclusion as
              ObjectLabelRenderer.tsx's own isLine and graphics/
              measurements type-prefix check - a pure graphic or a wire
              has nothing to bind to a device. Every device is offered
              regardless of the symbol's own type: nothing in
              SymbolRegistry.ts's SymbolDefinition currently says which
              DeviceBehavior a symbol implies, so there is no
              unambiguous case to narrow the list by (a documented
              judgment call, not a missing feature). */}
          {(() => {
            const def = getSymbolDefinition(selectedObj.type);
            if (!def || def.isLine || selectedObj.type.startsWith('graphics.') || selectedObj.type.startsWith('measurements.')) return null;
            const deviceMissing = !!selectedObj.deviceId && !devices.some(d => d.id === selectedObj.deviceId);
            return (
              <div className="property-row">
                <label>Device</label>
                <select
                  value={selectedObj.deviceId || ''}
                  onChange={handleDeviceChange}
                  style={deviceMissing ? { color: 'var(--scada-alarm)' } : undefined}
                >
                  <option value="">(none)</option>
                  {deviceMissing && <option value={selectedObj.deviceId}>{selectedObj.deviceId} (does not exist)</option>}
                  {devices.map(d => <option key={d.id} value={d.id}>{d.id} - {d.designation}</option>)}
                </select>
                {/* feat/device-form-from-canvas commit 2a: same shared
                    openDeviceForm the symbol's own double-click uses -
                    disabled when there is no device to open at all. */}
                <button
                  onClick={() => useStore.getState().openDeviceForm(selectedObj.deviceId!, `Panel Properties, symbol ${describeObject(selectedObj)}`)}
                  disabled={!selectedObj.deviceId}
                  title="Open this device's form"
                  style={{ fontSize: UI_SMALL }}
                >
                  Open...
                </button>
              </div>
            );
          })()}
          <div className="property-row">
            <label>Description</label>
            <input type="text" name="description" value={selectedObj.description || ''} onChange={handleChange} onBlur={() => useStore.getState().saveHistory()} />
          </div>
          <div className="property-row">
            <label>Visible</label>
            <input type="checkbox" name="visible" checked={selectedObj.visible !== false} onChange={handleChange} onBlur={() => useStore.getState().saveHistory()} />
          </div>
          <div className="property-row">
            <label>Locked</label>
            <input type="checkbox" name="locked" checked={selectedObj.locked === true} onChange={handleChange} onBlur={() => useStore.getState().saveHistory()} />
          </div>
          <div className="property-row">
            <label>Z-Index</label>
            <input type="number" name="zIndex" value={selectedObj.zIndex || 0} onChange={handleChange} onBlur={() => useStore.getState().saveHistory()} />
          </div>
        </div>

        <div className="property-group">
          <div className="property-group-title">Layout</div>
          <div className="property-row">
            <label>Width</label>
            <input
              type="number"
              value={Math.round(selectedObj.width)}
              onChange={(e) => {
                const newWidth = parseFloat(e.target.value);
                if (isNaN(newWidth)) return;
                // The old busbar-resize special case (resizeBusbar,
                // dyn_top_NN port reattachment) is gone under the node-
                // based wiring model - a busbar is a BUS-style wire now,
                // resized by dragging its own endpoint.
                updateObject(selectedObj.id, { width: newWidth });
              }}
              onBlur={() => useStore.getState().saveHistory()}
            />
          </div>
          {/* feat/appearance-selection-frames commit 4b: for the static
              scada.meter symbol, obj.height is never actually read -
              ScadaMeterAdapter passes only obj.width into MeterSymbol,
              which computes its own height from row count
              (getMeterHeight), exactly like the dynamic meter/signal
              panel elements do. Editing this field DID silently
              overwrite the stored obj.height value - it just never had
              any visible effect, since nothing ever read it back. Only
              hidden for this one type; every other object's own Height
              field is real and stays. */}
          {selectedObj.type !== 'scada.meter' && (
            <div className="property-row">
              <label>Height</label>
              <input
                type="number"
                value={Math.round(selectedObj.height)}
                onChange={(e) => {
                  const newHeight = parseFloat(e.target.value);
                  if (!isNaN(newHeight)) updateObject(selectedObj.id, { height: newHeight });
                }}
                onBlur={() => useStore.getState().saveHistory()}
              />
            </div>
          )}
          <div className="property-row">
            <label>X</label>
            <input type="number" name="x" value={Math.round(selectedObj.x)} onChange={handleChange} onBlur={() => useStore.getState().saveHistory()} />
          </div>
          <div className="property-row">
            <label>Y</label>
            <input type="number" name="y" value={Math.round(selectedObj.y)} onChange={handleChange} onBlur={() => useStore.getState().saveHistory()} />
          </div>
          <div className="property-row">
            <label>Rotation</label>
            <input type="number" name="rotation" value={Math.round(selectedObj.rotation || 0)} onChange={handleChange} onBlur={() => useStore.getState().saveHistory()} />
          </div>
          <div className="property-row">
            <label>Scale X</label>
            <input type="number" name="scaleX" value={selectedObj.scaleX || 1} step="0.1" onChange={handleChange} onBlur={() => useStore.getState().saveHistory()} />
          </div>
          <div className="property-row">
            <label>Scale Y</label>
            <input type="number" name="scaleY" value={selectedObj.scaleY || 1} step="0.1" onChange={handleChange} onBlur={() => useStore.getState().saveHistory()} />
          </div>
        </div>

        <div className="property-group">
          <div className="property-group-title">Appearance</div>
          <div className="property-row">
            <label>Fill</label>
            <input type="color" name="fill" value={selectedObj.fill || '#ffffff'} onChange={handleChange} onBlur={() => useStore.getState().saveHistory()} />
          </div>
          <div className="property-row">
            <label>Border</label>
            <input type="color" name="border" value={selectedObj.border || '#000000'} onChange={handleChange} onBlur={() => useStore.getState().saveHistory()} />
          </div>
          {symbolUsesTextField(selectedObj.type) && (
            <div className="property-row">
              <label>Text</label>
              <input type="text" name="text" value={selectedObj.text || ''} onChange={handleChange} onBlur={() => useStore.getState().saveHistory()} />
            </div>
          )}
          <div className="property-row">
            <label>Font</label>
            <input type="text" name="font" value={selectedObj.font || 'Arial'} onChange={handleChange} onBlur={() => useStore.getState().saveHistory()} />
          </div>
          <div className="property-row">
            <label>Font Size</label>
            <input type="number" name="fontSize" value={selectedObj.fontSize || FONT_SIZE_BASE} onChange={handleChange} onBlur={() => useStore.getState().saveHistory()} />
          </div>
          <div className="property-row">
            <label>Tooltip</label>
            <input type="text" name="tooltip" value={selectedObj.tooltip || ''} onChange={handleChange} onBlur={() => useStore.getState().saveHistory()} />
          </div>
        </div>

        <div className="property-group">
          <div className="property-group-title">Editor Preview</div>
          <div className="property-row">
            <label>State</label>
            <select name="editor.preview_state" value={selectedObj.editor?.preview_state || ''} onChange={handleChange} onBlur={() => useStore.getState().saveHistory()}>
              <option value="">(Default)</option>
              {getSymbolDefinition(selectedObj.type)?.allowedStates.map(st => (
                <option key={st} value={st}>{st}</option>
              ))}
            </select>
          </div>
          {selectedObj.category === 'Measurements' || selectedObj.type.startsWith('measurements.') ? (
            <>
              <div className="property-row">
                <label>Value</label>
                <input type="text" name="editor.preview_value" value={selectedObj.editor?.preview_value || ''} onChange={handleChange} onBlur={() => useStore.getState().saveHistory()} />
              </div>
              <div className="property-row">
                <label>Unit</label>
                <input type="text" name="editor.unit" value={selectedObj.editor?.unit || ''} onChange={handleChange} onBlur={() => useStore.getState().saveHistory()} />
              </div>
              <div className="property-row">
                <label>Format</label>
                <input type="text" name="editor.format" placeholder="e.g. 0.0" value={selectedObj.editor?.format || ''} onChange={handleChange} onBlur={() => useStore.getState().saveHistory()} />
              </div>
            </>
          ) : null}
        </div>

        {/* feat/appearance-selection-frames commit 4d: the static
            scada.meter symbol takes its data through its own rows
            (obj.meterRows), not through a tag binding - ScadaMeterAdapter
            never reads obj.bindings at all, so this section did nothing
            for it but invite a user to fill in tags that would never be
            read. The dynamic meter/signal panel elements (their own
            selectedMeter/selectedSignalPanel branches above) never had a
            Bindings section to begin with - same reasoning, same fix,
            nothing further to remove there. */}
        {selectedObj.type !== 'scada.meter' && (
          <div className="property-group">
            <div className="property-group-title">Bindings</div>
            <div className="property-row">
              <label>State</label>
              <input type="text" name="bindings.state.tag" value={selectedObj.bindings?.state?.tag || ''} onChange={handleChange} onBlur={() => useStore.getState().saveHistory()} />
            </div>
            <div className="property-row">
              <label>Value</label>
              <input type="text" name="bindings.value.tag" value={selectedObj.bindings?.value?.tag || ''} onChange={handleChange} onBlur={() => useStore.getState().saveHistory()} />
            </div>
            <div className="property-row">
              <label>Alarm</label>
              <input type="text" name="bindings.alarm.tag" value={selectedObj.bindings?.alarm?.tag || ''} onChange={handleChange} onBlur={() => useStore.getState().saveHistory()} />
            </div>
            <div className="property-row">
              <label>Command</label>
              <input type="text" name="bindings.command.tag" value={selectedObj.bindings?.command?.tag || ''} onChange={handleChange} onBlur={() => useStore.getState().saveHistory()} />
            </div>
          </div>
        )}

        {selectedObj.type === 'scada.meter' && (
          <div className="property-group">
            <div className="property-group-title">
              Meter Rows
              <button onClick={addMeterRow} style={{marginLeft: 'auto', fontSize: UI_SMALL}}>+ Row</button>
            </div>
            {(selectedObj.meterRows || []).map((row, index) => (
              <div className="property-row" key={index} style={{ gap: '2px' }}>
                <input
                  type="text"
                  placeholder="Label"
                  value={row.label}
                  onChange={(e) => updateMeterRow(index, 'label', e.target.value)}
                  onBlur={() => useStore.getState().saveHistory()}
                  style={{ flex: 2 }}
                />
                <input
                  type="text"
                  placeholder="Value"
                  value={row.value}
                  onChange={(e) => updateMeterRow(index, 'value', e.target.value)}
                  onBlur={() => useStore.getState().saveHistory()}
                  style={{ flex: 1 }}
                />
                <input
                  type="text"
                  placeholder="Unit"
                  value={row.unit}
                  onChange={(e) => updateMeterRow(index, 'unit', e.target.value)}
                  onBlur={() => useStore.getState().saveHistory()}
                  style={{ flex: 1 }}
                />
                <button onClick={() => removeMeterRow(index)} style={{ fontSize: UI_SMALL }}>x</button>
              </div>
            ))}
            {(selectedObj.meterRows || []).length === 0 && (
              <div className="property-row"><em>No rows yet - use + Row to add one.</em></div>
            )}
          </div>
        )}

        {selectedObj.type === 'scada.boundary_point' && (
          <div className="property-group">
            <div className="property-group-title">Boundary Point</div>
            <div className="property-row">
              <label>Direction</label>
              <select name="boundaryDirection" value={selectedObj.boundaryDirection || 'SOURCE'} onChange={handleChange} onBlur={() => useStore.getState().saveHistory()}>
                <option value="SOURCE">Source</option>
                <option value="SINK">Sink</option>
              </select>
            </div>
            <div className="property-row">
              <label>Medium</label>
              <select name="boundaryMedium" value={selectedObj.boundaryMedium || 'ELECTRICAL'} onChange={handleChange} onBlur={() => useStore.getState().saveHistory()}>
                <option value="ELECTRICAL">Electrical</option>
                <option value="WATER">Water</option>
                <option value="VENTILATION">Ventilation</option>
              </select>
            </div>
            <div className="property-row">
              <label>Port Side</label>
              <select name="boundaryPortSide" value={selectedObj.boundaryPortSide || 'TOP'} onChange={handleChange} onBlur={() => useStore.getState().saveHistory()}>
                <option value="TOP">Top</option>
                <option value="BOTTOM">Bottom</option>
                <option value="LEFT">Left</option>
                <option value="RIGHT">Right</option>
              </select>
            </div>
            <div className="property-row"><em>Label/sublabel use Designation/Description above.</em></div>
          </div>
        )}

        <div className="property-group">
          <div className="property-group-title">
            Custom Properties
            <button onClick={addCustomProperty} style={{marginLeft: 'auto', fontSize: UI_SMALL}}>+</button>
          </div>
          {Object.entries(selectedObj.customProperties || {}).map(([key, value]) => (
            <div className="property-row" key={key}>
              <label>{key}</label>
              <input
                type="text"
                value={value as string}
                onChange={(e) => handleCustomPropertyChange(key, e.target.value)}
                onBlur={() => useStore.getState().saveHistory()}
              />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
