// feat/device-list-ui commit 2 - "Lista aparatow": the project-wide
// device table this whole task exists to build. Same modal convention as
// the other two dialogs in this feature (backdrop as a sibling, not a
// parent, of the dialog box).
//
// Row validity is read straight from validateDeviceRegistry run over the
// CURRENT store contents - this file never decides on its own whether a
// device is valid, it only colors rows and builds a tooltip from the
// issues that come back.

import React, { useMemo, useState } from 'react';
import { useStore } from '../store';
import type { Device, DeviceBehavior } from '../project/DeviceSchema';
import { validateDeviceRegistry } from '../project/DeviceValidation';
import { getDeviceIOFields } from '../project/DeviceFieldMap';
import { getDeviceLocationCode, getTotalChannelCount, getUsedChannelCount, getObjectUsageCounts } from '../project/DeviceRegistryQueries';
import { DeviceFormDialog } from './DeviceFormDialog';
import { FONT_SIZE_BASE, FONT_SIZE_SMALL, COLOR_ALARM } from '../theme/ScadaTheme';

const BEHAVIORS: DeviceBehavior[] = ['SWITCHED', 'SIGNAL', 'MEASURED', 'MODULATED', 'SELECTOR'];

type SortColumn = 'id' | 'designation' | 'name' | 'behavior' | 'kind';
// feat/device-form-from-canvas commit 2: 'edit' no longer has a local
// FormState of its own - Edytuj now calls the exact same shared
// openDeviceForm every other "aparat is visible" entry point calls
// (App.tsx renders the form for that case, see deviceFormSlice.ts).
// Only 'add' (Dodaj/Duplikuj) stays local: it has no existing device
// id to hand the shared mechanism, which is built entirely around
// editing one.
type FormState = { mode: 'add'; initialDevice?: Device } | null;

export interface DeviceListDialogProps {
  onClose: () => void;
}

export const DeviceListDialog: React.FC<DeviceListDialogProps> = ({ onClose }) => {
  const locations = useStore(s => s.locations);
  const cards = useStore(s => s.cards);
  const devices = useStore(s => s.devices);
  const objects = useStore(s => s.objects);
  const selectObjects = useStore(s => s.selectObjects);
  const addDevice = useStore(s => s.addDevice);
  const deleteDevice = useStore(s => s.deleteDevice);

  const [filterText, setFilterText] = useState('');
  const [filterLocation, setFilterLocation] = useState('');
  const [filterBehavior, setFilterBehavior] = useState<DeviceBehavior | ''>('');
  const [sortColumn, setSortColumn] = useState<SortColumn>('id');
  const [sortAsc, setSortAsc] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [form, setForm] = useState<FormState>(null);

  const validation = useMemo(() => validateDeviceRegistry({ locations, cards, devices }), [locations, cards, devices]);
  const issuesByDevice = useMemo(() => {
    const map = new Map<string, string[]>();
    for (const issue of validation.issues) {
      if (!issue.deviceId) continue;
      if (!map.has(issue.deviceId)) map.set(issue.deviceId, []);
      map.get(issue.deviceId)!.push(issue.message);
    }
    return map;
  }, [validation]);

  const filtered = useMemo(() => {
    const text = filterText.trim().toLowerCase();
    return devices.filter(d => {
      if (filterLocation && getDeviceLocationCode(d.id) !== filterLocation) return false;
      if (filterBehavior && d.behavior !== filterBehavior) return false;
      if (text && !(`${d.id} ${d.designation} ${d.name} ${d.kind}`.toLowerCase().includes(text))) return false;
      return true;
    });
  }, [devices, filterText, filterLocation, filterBehavior]);

  const sorted = useMemo(() => {
    const copy = [...filtered];
    copy.sort((a, b) => {
      const av = String(a[sortColumn] ?? '');
      const bv = String(b[sortColumn] ?? '');
      const cmp = av.localeCompare(bv);
      return sortAsc ? cmp : -cmp;
    });
    return copy;
  }, [filtered, sortColumn, sortAsc]);

  const handleSort = (col: SortColumn) => {
    if (col === sortColumn) setSortAsc(!sortAsc);
    else { setSortColumn(col); setSortAsc(true); }
  };

  const handleDelete = () => {
    if (!selectedId) return;
    if (!confirm(`Usunac aparat '${selectedId}'?`)) return;
    deleteDevice(selectedId);
    setSelectedId(null);
  };

  const handleDuplicate = () => {
    const device = devices.find(d => d.id === selectedId);
    if (!device) return;
    // Mandatory test: duplicating clears id and designation only - every
    // other field (name, kind, behavior, publishToHa, behavior-specific
    // fields) carries over unchanged into the new draft.
    const draft: Device = { ...device, id: '', designation: '' };
    setForm({ mode: 'add', initialDevice: draft });
  };

  const handleSaveForm = (device: Device) => {
    // Only 'add' (Dodaj/Duplikuj) ever reaches here now - Edytuj's own
    // save goes through App.tsx's shared onSave (deviceFormSlice.ts),
    // the exact same path every other entry point uses.
    addDevice(device);
    setForm(null);
  };

  // feat/device-form-from-canvas commit 2: Edytuj now opens the SAME
  // form every other "aparat is visible" place opens - no sourceContext,
  // so DeviceFormDialog's own header stays exactly what it always was
  // for this path.
  const handleEdit = () => {
    if (!selectedId) return;
    useStore.getState().openDeviceForm(selectedId);
  };

  // feat/device-list-ui commit 5: how many placed screen symbols
  // (SynopticObject.deviceId - see PropertyInspector.tsx's Aparat
  // dropdown) currently reference each device. Purely a screen-side
  // lookup, unrelated to anything DeviceValidation.ts checks - the same
  // device used by several symbols is normal, not an error, per this
  // task's own architecture, so this only counts, it never flags.
  // fix/inline-device-creation commit 3: the count itself now lives in
  // DeviceRegistryQueries.ts (getObjectUsageCounts), shared with the
  // PRZYPISZ ISTNIEJACY device list.
  const usageCountByDevice = useMemo(() => getObjectUsageCounts(objects), [objects]);

  const handleNavigateToUsage = (deviceId: string) => {
    const first = objects.find(o => o.deviceId === deviceId);
    if (!first) return;
    selectObjects([first.id]);
    onClose();
  };

  const usedChannels = getUsedChannelCount(devices);
  const totalChannels = getTotalChannelCount(cards);
  const errorDeviceCount = issuesByDevice.size;

  const sortIndicator = (col: SortColumn) => col === sortColumn ? (sortAsc ? ' ▲' : ' ▼') : '';

  return (
    <>
      <div style={backdropStyle} onClick={onClose} />
      <div style={dialogStyle} onClick={(e) => e.stopPropagation()}>
        <div style={headerStyle}>
          <span>Lista aparatow</span>
          <button onClick={onClose} title="Zamknij" style={closeButtonStyle}>x</button>
        </div>

        <div style={toolbarStyle}>
          <input
            value={filterText}
            onChange={e => setFilterText(e.target.value)}
            placeholder="Szukaj..."
            style={{ flex: 1 }}
          />
          <select value={filterLocation} onChange={e => setFilterLocation(e.target.value)}>
            <option value="">Wszystkie lokalizacje</option>
            {locations.map(l => <option key={l.code} value={l.code}>{l.code}</option>)}
          </select>
          <select value={filterBehavior} onChange={e => setFilterBehavior(e.target.value as DeviceBehavior | '')}>
            <option value="">Wszystkie zachowania</option>
            {BEHAVIORS.map(b => <option key={b} value={b}>{b}</option>)}
          </select>
          <button onClick={() => setForm({ mode: 'add' })} disabled={locations.length === 0} title={locations.length === 0 ? 'Najpierw dodaj lokalizacje w Rejestrach projektu' : ''}>+ Dodaj</button>
          <button onClick={handleEdit} disabled={!selectedId}>Edytuj</button>
          <button onClick={handleDuplicate} disabled={!selectedId}>Duplikuj</button>
          <button onClick={handleDelete} disabled={!selectedId}>Usun</button>
        </div>

        <div style={bodyStyle}>
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thStyle} onClick={() => handleSort('id')}>Id{sortIndicator('id')}</th>
                <th style={thStyle} onClick={() => handleSort('designation')}>Oznaczenie{sortIndicator('designation')}</th>
                <th style={thStyle} onClick={() => handleSort('name')}>Nazwa{sortIndicator('name')}</th>
                <th style={thStyle} onClick={() => handleSort('behavior')}>Zachowanie{sortIndicator('behavior')}</th>
                <th style={thStyle} onClick={() => handleSort('kind')}>Rodzaj{sortIndicator('kind')}</th>
                <th style={thStyle}>Wejscia</th>
                <th style={thStyle}>Wyjscia</th>
                <th style={thStyle}>Uzycia</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map(device => {
                const issues = issuesByDevice.get(device.id) ?? [];
                const invalid = issues.length > 0;
                const { inputs, outputs } = getDeviceIOFields(device);
                const usageCount = usageCountByDevice.get(device.id) ?? 0;
                return (
                  <tr
                    key={device.id}
                    onClick={() => setSelectedId(device.id)}
                    title={invalid ? issues.join('\n') : undefined}
                    style={{
                      cursor: 'pointer',
                      background: selectedId === device.id ? 'var(--scada-value-field)' : undefined,
                      color: invalid ? COLOR_ALARM : undefined
                    }}
                  >
                    <td style={tdStyle}>{device.id || '(bez id)'}</td>
                    <td style={tdStyle}>{device.designation}</td>
                    <td style={tdStyle}>{device.name}</td>
                    <td style={tdStyle}>{device.behavior}</td>
                    <td style={tdStyle}>{device.kind}</td>
                    <td style={tdStyle}>{inputs.map(f => f.addr).join(', ')}</td>
                    <td style={tdStyle}>{outputs.map(f => f.addr).join(', ')}</td>
                    <td style={tdStyle}>
                      {usageCount > 0 ? (
                        <button onClick={(e) => { e.stopPropagation(); handleNavigateToUsage(device.id); }} title="Przejdz do pierwszego wystapienia na ekranie">
                          {usageCount}
                        </button>
                      ) : 0}
                    </td>
                  </tr>
                );
              })}
              {sorted.length === 0 && (
                <tr><td style={tdStyle} colSpan={8}>Brak aparatow spelniajacych kryteria.</td></tr>
              )}
            </tbody>
          </table>
        </div>

        <div style={footerStyle}>
          <span style={{ fontSize: `${FONT_SIZE_SMALL}px` }}>
            Aparaty: {devices.length} | Bledy: {errorDeviceCount} | Kanaly: {usedChannels}/{totalChannels}
          </span>
          <button onClick={onClose}>Zamknij</button>
        </div>
      </div>

      {form && (
        <DeviceFormDialog
          mode="add"
          initialDevice={form.initialDevice}
          onSave={handleSaveForm}
          onCancel={() => setForm(null)}
        />
      )}
    </>
  );
};

const backdropStyle: React.CSSProperties = {
  position: 'fixed', inset: 0, background: 'var(--scada-outline)', opacity: 0.5, zIndex: 1000
};

const dialogStyle: React.CSSProperties = {
  position: 'fixed', top: '50%', left: '50%', transform: 'translate(-50%, -50%)',
  zIndex: 1001, width: '820px', maxHeight: '78vh', display: 'flex', flexDirection: 'column',
  background: 'var(--scada-panel)', border: '2px solid var(--scada-outline)', color: 'var(--scada-outline)',
  fontFamily: 'var(--scada-font-ui)', fontSize: 'var(--scada-font-size-base)'
};

const headerStyle: React.CSSProperties = {
  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
  padding: '8px 12px', borderBottom: '1px solid var(--scada-outline)', fontWeight: 'bold'
};

const closeButtonStyle: React.CSSProperties = { background: 'transparent', border: 'none', cursor: 'pointer' };

const toolbarStyle: React.CSSProperties = { display: 'flex', gap: '6px', padding: '8px 12px', borderBottom: '1px solid var(--scada-outline)' };

const bodyStyle: React.CSSProperties = { overflowY: 'auto', flex: 1, padding: '0 12px' };

const tableStyle: React.CSSProperties = { width: '100%', borderCollapse: 'collapse', fontSize: `${FONT_SIZE_BASE}px` };
const thStyle: React.CSSProperties = { textAlign: 'left', borderBottom: '1px solid var(--scada-outline)', padding: '2px 4px', cursor: 'pointer', userSelect: 'none' };
const tdStyle: React.CSSProperties = { padding: '2px 4px', borderBottom: '1px solid var(--scada-bevel-dark)' };

const footerStyle: React.CSSProperties = {
  display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px', padding: '8px 12px', borderTop: '1px solid var(--scada-outline)'
};
