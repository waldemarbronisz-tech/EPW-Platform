// fix/inline-device-creation commit 2: opened from ChannelAddressPicker's
// own "+ Karta" button, so a card can be added right at the channel
// picker that needed it, without leaving the device form. Same
// check-then-save path as DeviceRegistriesDialog.tsx's own Dodaj row -
// checkAddCard (DeviceRegistryMutations.ts) then the store's own addCard
// action, never a second copy of the format/uniqueness rule.
//
// channelKind is fixed to whichever kind the calling picker manages
// (expectedKind), not a free choice: this dialog only ever opens from a
// picker restricted to one specific kind, and the caller immediately
// selects the new card's first channel on success (emit(cardId, 1)) -
// letting the kind diverge from the picker's own would make that
// immediate selection either wrong or impossible. Cancelling calls
// onCancel without ever calling addCard, so nothing changes.
import React, { useState } from 'react';
import { useStore } from '../store';
import type { CardEntry, ChannelKind } from '../project/DeviceSchema';
import { checkAddCard } from '../project/DeviceRegistryMutations';
import { FONT_SIZE_SMALL, COLOR_ALARM } from '../theme/ScadaTheme';

export interface AddCardDialogProps {
  expectedKind: ChannelKind;
  onAdded: (cardId: string) => void;
  onCancel: () => void;
}

export const AddCardDialog: React.FC<AddCardDialogProps> = ({ expectedKind, onAdded, onCancel }) => {
  const locations = useStore(s => s.locations);
  const cards = useStore(s => s.cards);
  const devices = useStore(s => s.devices);
  const addCard = useStore(s => s.addCard);

  const [id, setId] = useState('');
  const [model, setModel] = useState('');
  const [channelCount, setChannelCount] = useState(16);
  const [error, setError] = useState<string | null>(null);

  const handleAdd = () => {
    const candidate: CardEntry = { id, model, channelKind: expectedKind, channelCount };
    const outcome = checkAddCard(candidate, locations, cards, devices);
    if (!outcome.ok) {
      setError(outcome.issue.message);
      return;
    }
    addCard(candidate);
    onAdded(candidate.id);
  };

  return (
    <>
      <div style={backdropStyle} onClick={onCancel} />
      <div style={dialogStyle} onClick={(e) => e.stopPropagation()}>
        <div style={headerStyle}>New Card</div>
        <div style={bodyStyle}>
          <div className="property-row">
            <label>Id</label>
            <input autoFocus value={id} onChange={e => setId(e.target.value)} style={inputStyle} placeholder="ELA1" />
          </div>
          <div className="property-row">
            <label>Model</label>
            <input value={model} onChange={e => setModel(e.target.value)} style={inputStyle} placeholder="ELA01" />
          </div>
          <div className="property-row">
            <label>Channel Kind</label>
            <input value={expectedKind} disabled style={inputStyle} />
          </div>
          <div className="property-row">
            <label>Channel Count</label>
            <input type="number" value={channelCount} onChange={e => setChannelCount(Number(e.target.value))} style={inputStyle} />
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
