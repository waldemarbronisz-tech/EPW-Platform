// fix/inline-device-creation commit 2: opened from a button next to
// DeviceFormDialog.tsx's own location <select>, so a location can be
// added without leaving the device form. Uses the exact same check and
// save path as DeviceRegistriesDialog.tsx's own Dodaj row -
// checkAddLocation (DeviceRegistryMutations.ts) then the store's own
// addLocation action - never a second copy of the format/uniqueness
// rule. Cancelling calls onCancel without ever calling addLocation, so
// nothing changes; confirming calls onAdded(code) so the caller can
// select the new location immediately, without losing whatever else
// was already filled in the device form.
import React, { useState } from 'react';
import { useStore } from '../store';
import type { LocationEntry } from '../project/DeviceSchema';
import { checkAddLocation } from '../project/DeviceRegistryMutations';
import { FONT_SIZE_SMALL, COLOR_ALARM } from '../theme/ScadaTheme';

export interface AddLocationDialogProps {
  onAdded: (code: string) => void;
  onCancel: () => void;
}

export const AddLocationDialog: React.FC<AddLocationDialogProps> = ({ onAdded, onCancel }) => {
  const locations = useStore(s => s.locations);
  const cards = useStore(s => s.cards);
  const devices = useStore(s => s.devices);
  const addLocation = useStore(s => s.addLocation);

  const [code, setCode] = useState('');
  const [description, setDescription] = useState('');
  const [error, setError] = useState<string | null>(null);

  const handleAdd = () => {
    const candidate: LocationEntry = { code, description };
    const outcome = checkAddLocation(candidate, locations, cards, devices);
    if (!outcome.ok) {
      setError(outcome.issue.message);
      return;
    }
    addLocation(candidate);
    onAdded(candidate.code);
  };

  return (
    <>
      <div style={backdropStyle} onClick={onCancel} />
      <div style={dialogStyle} onClick={(e) => e.stopPropagation()}>
        <div style={headerStyle}>New Location</div>
        <div style={bodyStyle}>
          <div className="property-row">
            <label>Code</label>
            <input autoFocus value={code} onChange={e => setCode(e.target.value)} style={inputStyle} placeholder="KOT" />
          </div>
          <div className="property-row">
            <label>Description</label>
            <input value={description} onChange={e => setDescription(e.target.value)} style={inputStyle} placeholder="Boiler room" />
          </div>
          {error && <div style={errorStyle}>{error}</div>}
        </div>
        <div style={footerStyle}>
          <button onClick={onCancel}>Cancel</button>
          <button onClick={handleAdd}>Add</button>
        </div>
      </div>
    </>
  );
};

const backdropStyle: React.CSSProperties = {
  position: 'fixed', inset: 0, background: 'var(--scada-outline)', opacity: 0.5, zIndex: 1010
};

const dialogStyle: React.CSSProperties = {
  position: 'fixed', top: '50%', left: '50%', transform: 'translate(-50%, -50%)',
  zIndex: 1011, width: '320px', display: 'flex', flexDirection: 'column',
  background: 'var(--scada-panel)', border: '2px solid var(--scada-outline)', color: 'var(--scada-outline)',
  fontFamily: 'var(--scada-font-ui)', fontSize: 'var(--scada-font-size-base)'
};

const headerStyle: React.CSSProperties = {
  padding: '8px 12px', borderBottom: '1px solid var(--scada-outline)', fontWeight: 'bold'
};

const bodyStyle: React.CSSProperties = { padding: '8px 12px' };
const inputStyle: React.CSSProperties = { width: '100%', fontSize: 'var(--scada-font-size-base)' };
const errorStyle: React.CSSProperties = { color: COLOR_ALARM, fontSize: `${FONT_SIZE_SMALL}px`, marginTop: '6px' };

const footerStyle: React.CSSProperties = {
  display: 'flex', justifyContent: 'flex-end', gap: '8px', padding: '8px 12px', borderTop: '1px solid var(--scada-outline)'
};
