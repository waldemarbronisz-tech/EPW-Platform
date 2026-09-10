// fix/inline-device-creation commit 3: DeviceFormDialog.tsx's own
// PRZYPISZ ISTNIEJACY mode - a project-wide, searchable device list,
// pre-filtered by behavior matching the originating symbol's own
// suggested behavior (togglable off). Selecting a row and confirming
// (the caller's own footer "Przypisz" button, not anything in this
// component) assigns that device to the symbol - the SAME device
// already used by other symbols is explicitly valid, never flagged,
// per this whole project's own established architecture (a device
// exists independently of any symbol; a symbol only references one by
// id) - this list's own usage count column exists to make that visible,
// not to warn against it.
import React, { useMemo, useState } from 'react';
import type { Device, DeviceBehavior } from '../project/DeviceSchema';
import { getObjectUsageCounts } from '../project/DeviceRegistryQueries';
import { FONT_SIZE_BASE } from '../theme/ScadaTheme';

export interface AssignExistingDeviceListProps {
  devices: Device[];
  objects: { deviceId?: string }[];
  // The symbol's own suggested behavior (SymbolBehaviorMapping.ts) -
  // undefined when the symbol type is outside that mapping, in which
  // case there is nothing to pre-filter by and the checkbox itself is
  // not shown at all.
  suggestedBehavior?: DeviceBehavior;
  selectedId: string | null;
  onSelect: (deviceId: string) => void;
}

export const AssignExistingDeviceList: React.FC<AssignExistingDeviceListProps> = ({ devices, objects, suggestedBehavior, selectedId, onSelect }) => {
  const [search, setSearch] = useState('');
  const [filterByBehavior, setFilterByBehavior] = useState(!!suggestedBehavior);

  const usageCounts = useMemo(() => getObjectUsageCounts(objects), [objects]);

  const filtered = useMemo(() => {
    const text = search.trim().toLowerCase();
    return devices.filter(d => {
      if (filterByBehavior && suggestedBehavior && d.behavior !== suggestedBehavior) return false;
      if (text && !`${d.id} ${d.designation} ${d.name}`.toLowerCase().includes(text)) return false;
      return true;
    });
  }, [devices, search, filterByBehavior, suggestedBehavior]);

  return (
    <div style={{ padding: '8px 12px' }}>
      <div className="property-row">
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search by id, designation or name..."
          style={{ flex: 1 }}
        />
      </div>
      {suggestedBehavior && (
        <div className="property-row">
          <label>
            <input type="checkbox" checked={filterByBehavior} onChange={e => setFilterByBehavior(e.target.checked)} />
            {` Only behaviour ${suggestedBehavior}`}
          </label>
        </div>
      )}
      <table style={tableStyle}>
        <thead>
          <tr>
            <th style={thStyle}>Id</th>
            <th style={thStyle}>Designation</th>
            <th style={thStyle}>Name</th>
            <th style={thStyle}>Uses</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map(d => (
            <tr
              key={d.id}
              onClick={() => onSelect(d.id)}
              style={{ cursor: 'pointer', background: selectedId === d.id ? 'var(--scada-value-field)' : undefined }}
            >
              <td style={tdStyle}>{d.id}</td>
              <td style={tdStyle}>{d.designation}</td>
              <td style={tdStyle}>{d.name}</td>
              <td style={tdStyle}>{usageCounts.get(d.id) ?? 0}</td>
            </tr>
          ))}
          {filtered.length === 0 && (
            <tr><td style={tdStyle} colSpan={4}>No devices match these criteria.</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
};

const tableStyle: React.CSSProperties = { width: '100%', borderCollapse: 'collapse', fontSize: `${FONT_SIZE_BASE}px` };
const thStyle: React.CSSProperties = { textAlign: 'left', borderBottom: '1px solid var(--scada-outline)', padding: '2px 4px' };
const tdStyle: React.CSSProperties = { padding: '2px 4px', borderBottom: '1px solid var(--scada-bevel-dark)' };
