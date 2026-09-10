// feat/editing-and-signal-panel commit 8: the signal-picker wizard,
// grouped by location - mirrors MeterWizardDialog.tsx's own tree-with-
// checkboxes pattern almost exactly; see SignalPanelWizard.ts's header
// comment for why this groups by location instead of by unit.
//
// Plain HTML overlay, not Konva - same reasoning as MeterWizardDialog.tsx.

import React, { useState } from 'react';
import { useStore } from '../store';
import type { Device } from '../project/DeviceSchema';
import { groupSignalCapableDevicesByLocation, buildSignalPanelRowsFromSelection } from '../elements/SignalPanelWizard';
import type { SignalPanelRow } from '../elements/SignalPanelElement';
import { FONT_SIZE_BASE, FONT_SIZE_SMALL } from '../theme/ScadaTheme';

export interface SignalPanelWizardDialogProps {
  devices: Device[];
  onConfirm: (rows: SignalPanelRow[]) => void;
  onAddManualRow: () => void;
  onCancel: () => void;
}

export const SignalPanelWizardDialog: React.FC<SignalPanelWizardDialogProps> = ({ devices, onConfirm, onAddManualRow, onCancel }) => {
  const groups = groupSignalCapableDevicesByLocation(devices);
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set(groups.map(g => g.location)));
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const toggleExpanded = (location: string) => {
    setExpanded(prev => {
      const next = new Set(prev);
      if (next.has(location)) next.delete(location); else next.add(location);
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
    onConfirm(buildSignalPanelRowsFromSelection(groups, selected));
  };

  return (
    <>
      {/* A sibling of the dialog below, not its parent - see
          MeterWizardDialog.tsx's own comment on why. */}
      <div style={backdropStyle} onClick={onCancel} />
      <div style={dialogStyle} onClick={(e) => e.stopPropagation()}>
        <div style={headerStyle}>
          <span>Signal Selection Wizard</span>
          <button onClick={onCancel} title="Cancel" style={closeButtonStyle}>x</button>
        </div>

        <div style={bodyStyle}>
          {groups.length === 0 ? (
            // No SIGNAL/SWITCHED devices in the project at all - explain
            // why the tree is empty instead of just showing nothing, and
            // offer the one thing still useful here: a manual row.
            <div style={{ padding: '12px' }}>
              <p>
                No devices with SIGNAL or SWITCHED behaviour in the project's
                device list. Define a signal device first, or add a manual
                row and set its state yourself.
              </p>
              <button onClick={() => { onAddManualRow(); onCancel(); }}>
                + Add manual row
              </button>
            </div>
          ) : (
            <>
              <div style={{ padding: '4px 12px' }}>
                <button onClick={selectAll}>Select all</button>
                <span style={{ marginLeft: '8px', fontSize: `${FONT_SIZE_SMALL}px` }}>
                  Selected: {selected.size}
                </span>
              </div>
              {groups.map(group => (
                <div key={group.location} style={{ padding: '0 12px' }}>
                  <div style={groupHeaderStyle} onClick={() => toggleExpanded(group.location)}>
                    <span>{expanded.has(group.location) ? '▼' : '▶'}</span>
                    <strong style={{ marginLeft: '6px' }}>{group.location}</strong>
                    <span style={{ marginLeft: '6px', fontSize: `${FONT_SIZE_SMALL}px` }}>({group.devices.length})</span>
                  </div>
                  {expanded.has(group.location) && (
                    <div style={{ paddingLeft: '20px' }}>
                      {/* feat/device-form-from-canvas commit 2d: same
                          checkbox/double-click separation as
                          MeterWizardDialog.tsx's own tree - see that
                          file's comment for why a shared <label> around
                          both would let a double-click silently
                          toggle-then-toggle the checkbox instead of
                          leaving it alone. */}
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
                            onDoubleClick={() => useStore.getState().openDeviceForm(device.id, 'Signal Selection Wizard')}
                            title="Double-click: open this device's form"
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
            <button onClick={onCancel}>Cancel</button>
            <button onClick={handleConfirm} disabled={selected.size === 0}>
              Add {selected.size > 0 ? `(${selected.size})` : ''}
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
