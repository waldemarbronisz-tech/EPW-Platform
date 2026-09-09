// feat/meter-element part C: the measurement-picker wizard, modeled on
// e2TANGO-Studio's own device-tree-with-checkboxes pattern - a tree of
// unit groups, a checkbox per device, confirm adds everything checked
// in one go, cancel changes nothing at all.
//
// Plain HTML overlay, not Konva: a collapsible tree with checkboxes is
// exactly the kind of form UI the DOM already does well, the same
// reasoning PropertyInspector.tsx's own plain <input>/<select> fields
// already follow for this app's chrome. Colors come from the CSS
// bridge ScadaTheme.ts's own applyScadaCssVariables sets up (see that
// file's header comment) - var(--scada-*) throughout, nothing hand-
// picked here.

import React, { useState } from 'react';
import { useStore } from '../store';
import type { Device } from '../project/DeviceSchema';
import { groupMeasuredDevicesByUnit, buildRowsFromSelection } from '../meter/MeterWizard';
import type { MeterElementRow } from '../meter/MeterElement';
import { FONT_SIZE_BASE, FONT_SIZE_SMALL } from '../theme/ScadaTheme';

export interface MeterWizardDialogProps {
  devices: Device[];
  onConfirm: (rows: MeterElementRow[]) => void;
  onAddManualRow: () => void;
  onCancel: () => void;
}

export const MeterWizardDialog: React.FC<MeterWizardDialogProps> = ({ devices, onConfirm, onAddManualRow, onCancel }) => {
  const groups = groupMeasuredDevicesByUnit(devices);
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set(groups.map(g => g.unit)));
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const toggleExpanded = (unit: string) => {
    setExpanded(prev => {
      const next = new Set(prev);
      if (next.has(unit)) next.delete(unit); else next.add(unit);
      return next;
    });
  };

  const toggleSelected = (id: string) => {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const selectAll = () => {
    const all = new Set<string>();
    groups.forEach(g => g.devices.forEach(d => all.add(d.id)));
    setSelected(all);
  };

  const handleConfirm = () => {
    onConfirm(buildRowsFromSelection(groups, selected));
  };

  return (
    <>
      {/* A sibling of the dialog below, not its parent - opacity creates
          a stacking context that would wash out any DOM descendant, so
          the dialog stays opaque only by living outside this element's
          subtree entirely, not by any z-index/position trick alone. */}
      <div style={backdropStyle} onClick={onCancel} />
      <div style={dialogStyle} onClick={(e) => e.stopPropagation()}>
        <div style={headerStyle}>
          <span>Kreator wyboru pomiarow</span>
          <button onClick={onCancel} title="Anuluj" style={closeButtonStyle}>x</button>
        </div>

        <div style={bodyStyle}>
          {groups.length === 0 ? (
            // No MEASURED devices in the project at all - explain why the
            // tree is empty instead of just showing nothing, and offer
            // the one thing still useful here: a manual row.
            <div style={{ padding: '12px' }}>
              <p>
                Brak aparatow o zachowaniu MEASURED w liscie aparatow projektu.
                Najpierw zdefiniuj aparaty pomiarowe, albo dodaj wiersz reczny
                i wypelnij go wartosciami samodzielnie.
              </p>
              <button onClick={() => { onAddManualRow(); onCancel(); }}>
                + Dodaj wiersz reczny
              </button>
            </div>
          ) : (
            <>
              <div style={{ padding: '4px 12px' }}>
                <button onClick={selectAll}>Zaznacz wszystko</button>
                <span style={{ marginLeft: '8px', fontSize: `${FONT_SIZE_SMALL}px` }}>
                  Zaznaczono: {selected.size}
                </span>
              </div>
              {groups.map(group => (
                <div key={group.unit} style={{ padding: '0 12px' }}>
                  <div style={groupHeaderStyle} onClick={() => toggleExpanded(group.unit)}>
                    <span>{expanded.has(group.unit) ? '▼' : '▶'}</span>
                    <strong style={{ marginLeft: '6px' }}>{group.unit}</strong>
                    <span style={{ marginLeft: '6px', fontSize: `${FONT_SIZE_SMALL}px` }}>({group.devices.length})</span>
                  </div>
                  {expanded.has(group.unit) && (
                    <div style={{ paddingLeft: '20px' }}>
                      {/* feat/device-form-from-canvas commit 2d: the
                          checkbox and the "open this device's form" zone
                          are deliberately two separate elements, not one
                          <label> wrapping both - a <label> around an
                          <input type="checkbox"> makes ANY click inside it
                          (both clicks of a double-click included) toggle
                          the checkbox via native label-for-input
                          semantics, so a double-click on the device name
                          would silently toggle-then-toggle it (a checkbox
                          that never visibly changes, not a reliable
                          "leaves it alone"). Splitting them into a
                          checkbox-only label and a plain, structurally
                          unrelated sibling <span> means a double-click on
                          the span can never touch the checkbox at all,
                          regardless of click timing. */}
                      {group.devices.map(device => (
                        <div key={device.id} style={rowLabelStyle}>
                          <label style={{ display: 'flex', alignItems: 'center' }}>
                            <input
                              type="checkbox"
                              checked={selected.has(device.id)}
                              onChange={() => toggleSelected(device.id)}
                            />
                          </label>
                          <span
                            style={{ marginLeft: '6px', cursor: 'pointer' }}
                            onDoubleClick={() => useStore.getState().openDeviceForm(device.id, 'Kreator wyboru pomiarow')}
                            title="Dwuklik: otworz formularz tego aparatu"
                          >
                            {device.designation} - {device.name}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </>
          )}
        </div>

        {groups.length > 0 && (
          <div style={footerStyle}>
            <button onClick={onCancel}>Anuluj</button>
            <button onClick={handleConfirm} disabled={selected.size === 0}>
              Dodaj {selected.size > 0 ? `(${selected.size})` : ''}
            </button>
          </div>
        )}
      </div>
    </>
  );
};

const backdropStyle: React.CSSProperties = {
  position: 'fixed', inset: 0, background: 'var(--scada-outline)', opacity: 0.5, zIndex: 1000
};

const dialogStyle: React.CSSProperties = {
  position: 'fixed', top: '50%', left: '50%', transform: 'translate(-50%, -50%)',
  zIndex: 1001, width: '420px', maxHeight: '70vh', display: 'flex', flexDirection: 'column',
  background: 'var(--scada-panel)', border: '2px solid var(--scada-outline)', color: 'var(--scada-outline)'
};

const headerStyle: React.CSSProperties = {
  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
  padding: '8px 12px', borderBottom: '1px solid var(--scada-outline)', fontWeight: 'bold'
};

const closeButtonStyle: React.CSSProperties = { background: 'transparent', border: 'none', cursor: 'pointer' };

const bodyStyle: React.CSSProperties = { overflowY: 'auto', flex: 1 };

const groupHeaderStyle: React.CSSProperties = {
  display: 'flex', alignItems: 'center', padding: '4px 0', cursor: 'pointer'
};

const rowLabelStyle: React.CSSProperties = { display: 'flex', alignItems: 'center', padding: '2px 0', fontSize: `${FONT_SIZE_BASE}px` };

const footerStyle: React.CSSProperties = {
  display: 'flex', justifyContent: 'flex-end', gap: '8px', padding: '8px 12px', borderTop: '1px solid var(--scada-outline)'
};
