// feat/device-list-ui commit 1: "Rejestry projektu" - the two lists a
// device's own id and channel addresses are validated against
// (DeviceValidation.ts's validateDeviceId/validateChannelAddress):
// locations and cards. Same modal convention as MeterWizardDialog.tsx
// (backdrop as a sibling, not a parent, of the dialog box - see that
// file's own header comment for why).
//
// Every add/edit here is checked by building a full candidate registry
// (this tab's own pending list plus the store's other two lists
// unchanged) and running it through validateDeviceRegistry - the ONLY
// place a location code's or a card id's format/uniqueness rule is
// decided, per GRANICE ("nie powielaj regul walidacji w kodzie
// interfejsu"). This file only reads the resulting issues back out and
// shows them next to the field they are about; it never decides on its
// own that a code is well-formed or a card id is taken.
//
// Deleting a location or a card that some device still references is
// blocked outright, not merely confirmed - DeviceRegistryQueries.ts's
// usage queries (a plain lookup, not a validation rule) answer "is this
// still in use", and the button stays disabled with the usage count
// shown rather than opening a confirmation the user could click through.

import React, { useState } from 'react';
import { useStore } from '../store';
import type { LocationEntry, CardEntry, ChannelKind } from '../project/DeviceSchema';
import { validateDeviceRegistry } from '../project/DeviceValidation';
import { checkAddLocation, checkAddCard, issuesMentioning } from '../project/DeviceRegistryMutations';
import { getDevicesUsingLocation, getChannelUsagesForCard } from '../project/DeviceRegistryQueries';
import { FONT_SIZE_BASE, FONT_SIZE_SMALL, COLOR_ALARM } from '../theme/ScadaTheme';

export interface DeviceRegistriesDialogProps {
  onClose: () => void;
}

const CHANNEL_KINDS: ChannelKind[] = ['DI', 'DO', 'AI', 'AO'];

export const DeviceRegistriesDialog: React.FC<DeviceRegistriesDialogProps> = ({ onClose }) => {
  const [tab, setTab] = useState<'locations' | 'cards'>('locations');
  const locations = useStore(s => s.locations);
  const cards = useStore(s => s.cards);
  const devices = useStore(s => s.devices);
  const addLocation = useStore(s => s.addLocation);
  const updateLocation = useStore(s => s.updateLocation);
  const deleteLocation = useStore(s => s.deleteLocation);
  const addCard = useStore(s => s.addCard);
  const updateCard = useStore(s => s.updateCard);
  const deleteCard = useStore(s => s.deleteCard);

  // ---- Locations ----
  const [newLocCode, setNewLocCode] = useState('');
  const [newLocDesc, setNewLocDesc] = useState('');
  const [locError, setLocError] = useState<string | null>(null);
  const [editingLocCode, setEditingLocCode] = useState<string | null>(null);
  const [editLocDesc, setEditLocDesc] = useState('');

  const handleAddLocation = () => {
    const candidate: LocationEntry = { code: newLocCode, description: newLocDesc };
    // fix/inline-device-creation commit 2: the check itself now lives in
    // DeviceRegistryMutations.ts, shared with DeviceFormDialog.tsx's own
    // AddLocationDialog - see that module's header for why.
    const outcome = checkAddLocation(candidate, locations, cards, devices);
    if (!outcome.ok) {
      setLocError(outcome.issue.message);
      return;
    }
    addLocation(candidate);
    setNewLocCode('');
    setNewLocDesc('');
    setLocError(null);
  };

  const startEditLocation = (loc: LocationEntry) => {
    setEditingLocCode(loc.code);
    setEditLocDesc(loc.description);
    setLocError(null);
  };

  const handleSaveLocationEdit = (code: string) => {
    const candidate: LocationEntry = { code, description: editLocDesc };
    const nextLocations = locations.map(l => l.code === code ? candidate : l);
    const result = validateDeviceRegistry({ locations: nextLocations, cards, devices });
    const relevant = issuesMentioning(result.issues, code);
    if (relevant.length > 0) {
      setLocError(relevant[0].message);
      return;
    }
    updateLocation(code, candidate);
    setEditingLocCode(null);
    setLocError(null);
  };

  const handleDeleteLocation = (code: string) => {
    const usedBy = getDevicesUsingLocation(devices, code);
    if (usedBy.length > 0) {
      setLocError(`Cannot delete location '${code}' - it is used by ${usedBy.length} device(s) (${usedBy.map(d => d.id).join(', ')}).`);
      return;
    }
    if (!confirm(`Delete location '${code}'?`)) return;
    deleteLocation(code);
    setLocError(null);
  };

  // ---- Cards ----
  const [newCardId, setNewCardId] = useState('');
  const [newCardModel, setNewCardModel] = useState('');
  const [newCardKind, setNewCardKind] = useState<ChannelKind>('DI');
  const [newCardCount, setNewCardCount] = useState(16);
  const [cardError, setCardError] = useState<string | null>(null);
  const [editingCardId, setEditingCardId] = useState<string | null>(null);
  const [editCardModel, setEditCardModel] = useState('');
  const [editCardKind, setEditCardKind] = useState<ChannelKind>('DI');
  const [editCardCount, setEditCardCount] = useState(16);

  const handleAddCard = () => {
    const candidate: CardEntry = { id: newCardId, model: newCardModel, channelKind: newCardKind, channelCount: newCardCount };
    // fix/inline-device-creation commit 2: shared with DeviceFormDialog.tsx's
    // own AddCardDialog (opened from ChannelAddressPicker.tsx) - see
    // DeviceRegistryMutations.ts's header for why.
    const outcome = checkAddCard(candidate, locations, cards, devices);
    if (!outcome.ok) {
      setCardError(outcome.issue.message);
      return;
    }
    addCard(candidate);
    setNewCardId('');
    setNewCardModel('');
    setNewCardKind('DI');
    setNewCardCount(16);
    setCardError(null);
  };

  const startEditCard = (card: CardEntry) => {
    setEditingCardId(card.id);
    setEditCardModel(card.model);
    setEditCardKind(card.channelKind);
    setEditCardCount(card.channelCount);
    setCardError(null);
  };

  const handleSaveCardEdit = (id: string) => {
    const candidate: CardEntry = { id, model: editCardModel, channelKind: editCardKind, channelCount: editCardCount };
    const nextCards = cards.map(c => c.id === id ? candidate : c);
    const result = validateDeviceRegistry({ locations, cards: nextCards, devices });
    const relevant = issuesMentioning(result.issues, id);
    if (relevant.length > 0) {
      setCardError(relevant[0].message);
      return;
    }
    updateCard(id, candidate);
    setEditingCardId(null);
    setCardError(null);
  };

  const handleDeleteCard = (id: string) => {
    const usages = getChannelUsagesForCard(devices, id);
    if (usages.length > 0) {
      const byDevice = Array.from(new Set(usages.map(u => u.deviceId)));
      setCardError(`Cannot delete card '${id}' - its channels are used by ${byDevice.length} device(s) (${byDevice.join(', ')}).`);
      return;
    }
    if (!confirm(`Delete card '${id}'?`)) return;
    deleteCard(id);
    setCardError(null);
  };

  return (
    <>
      <div style={backdropStyle} onClick={onClose} />
      <div style={dialogStyle} onClick={(e) => e.stopPropagation()}>
        <div style={headerStyle}>
          <span>Project Registers</span>
          <button onClick={onClose} title="Close" style={closeButtonStyle}>x</button>
        </div>

        <div style={tabBarStyle}>
          <div style={tab === 'locations' ? tabActiveStyle : tabInactiveStyle} onClick={() => setTab('locations')}>Locations</div>
          <div style={tab === 'cards' ? tabActiveStyle : tabInactiveStyle} onClick={() => setTab('cards')}>Cards</div>
        </div>

        <div style={bodyStyle}>
          {tab === 'locations' && (
            <div style={{ padding: '8px 12px' }}>
              <table style={tableStyle}>
                <thead>
                  <tr>
                    <th style={thStyle}>Code</th>
                    <th style={thStyle}>Description</th>
                    <th style={thStyle}>Usage</th>
                    <th style={thStyle}></th>
                  </tr>
                </thead>
                <tbody>
                  {locations.map(loc => {
                    const usedBy = getDevicesUsingLocation(devices, loc.code);
                    const editing = editingLocCode === loc.code;
                    return (
                      <tr key={loc.code}>
                        <td style={tdStyle}>{loc.code}</td>
                        <td style={tdStyle}>
                          {editing
                            ? <input value={editLocDesc} onChange={e => setEditLocDesc(e.target.value)} style={inputStyle} />
                            : loc.description}
                        </td>
                        <td style={tdStyle}>{usedBy.length}</td>
                        <td style={tdStyle}>
                          {editing ? (
                            <>
                              <button onClick={() => handleSaveLocationEdit(loc.code)}>Save</button>
                              <button onClick={() => { setEditingLocCode(null); setLocError(null); }}>Cancel</button>
                            </>
                          ) : (
                            <>
                              <button onClick={() => startEditLocation(loc)}>Edit</button>
                              <button onClick={() => handleDeleteLocation(loc.code)} disabled={usedBy.length > 0} title={usedBy.length > 0 ? `Used by ${usedBy.length} device(s)` : ''}>Delete</button>
                            </>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                  <tr>
                    <td style={tdStyle}><input value={newLocCode} onChange={e => setNewLocCode(e.target.value)} style={inputStyle} placeholder="KOT" /></td>
                    <td style={tdStyle}><input value={newLocDesc} onChange={e => setNewLocDesc(e.target.value)} style={inputStyle} placeholder="Boiler room" /></td>
                    <td style={tdStyle}></td>
                    <td style={tdStyle}><button onClick={handleAddLocation}>+ Add</button></td>
                  </tr>
                </tbody>
              </table>
              {locError && <div style={errorStyle}>{locError}</div>}
            </div>
          )}

          {tab === 'cards' && (
            <div style={{ padding: '8px 12px' }}>
              <table style={tableStyle}>
                <thead>
                  <tr>
                    <th style={thStyle}>Id</th>
                    <th style={thStyle}>Model</th>
                    <th style={thStyle}>Kind</th>
                    <th style={thStyle}>Channels</th>
                    <th style={thStyle}>Usage</th>
                    <th style={thStyle}></th>
                  </tr>
                </thead>
                <tbody>
                  {cards.map(card => {
                    const usages = getChannelUsagesForCard(devices, card.id);
                    const usedByCount = new Set(usages.map(u => u.deviceId)).size;
                    const editing = editingCardId === card.id;
                    return (
                      <tr key={card.id}>
                        <td style={tdStyle}>{card.id}</td>
                        <td style={tdStyle}>
                          {editing
                            ? <input value={editCardModel} onChange={e => setEditCardModel(e.target.value)} style={inputStyle} />
                            : card.model}
                        </td>
                        <td style={tdStyle}>
                          {editing
                            ? <select value={editCardKind} onChange={e => setEditCardKind(e.target.value as ChannelKind)} style={inputStyle}>
                                {CHANNEL_KINDS.map(k => <option key={k} value={k}>{k}</option>)}
                              </select>
                            : card.channelKind}
                        </td>
                        <td style={tdStyle}>
                          {editing
                            ? <input type="number" value={editCardCount} onChange={e => setEditCardCount(Number(e.target.value))} style={inputStyle} />
                            : card.channelCount}
                        </td>
                        <td style={tdStyle}>{usedByCount}</td>
                        <td style={tdStyle}>
                          {editing ? (
                            <>
                              <button onClick={() => handleSaveCardEdit(card.id)}>Save</button>
                              <button onClick={() => { setEditingCardId(null); setCardError(null); }}>Cancel</button>
                            </>
                          ) : (
                            <>
                              <button onClick={() => startEditCard(card)}>Edit</button>
                              <button onClick={() => handleDeleteCard(card.id)} disabled={usedByCount > 0} title={usedByCount > 0 ? `Used by ${usedByCount} device(s)` : ''}>Delete</button>
                            </>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                  <tr>
                    <td style={tdStyle}><input value={newCardId} onChange={e => setNewCardId(e.target.value)} style={inputStyle} placeholder="ELA1" /></td>
                    <td style={tdStyle}><input value={newCardModel} onChange={e => setNewCardModel(e.target.value)} style={inputStyle} placeholder="ELA01" /></td>
                    <td style={tdStyle}>
                      <select value={newCardKind} onChange={e => setNewCardKind(e.target.value as ChannelKind)} style={inputStyle}>
                        {CHANNEL_KINDS.map(k => <option key={k} value={k}>{k}</option>)}
                      </select>
                    </td>
                    <td style={tdStyle}><input type="number" value={newCardCount} onChange={e => setNewCardCount(Number(e.target.value))} style={inputStyle} /></td>
                    <td style={tdStyle}></td>
                    <td style={tdStyle}><button onClick={handleAddCard}>+ Add</button></td>
                  </tr>
                </tbody>
              </table>
              {cardError && <div style={errorStyle}>{cardError}</div>}
            </div>
          )}
        </div>

        <div style={footerStyle}>
          <button onClick={onClose}>Close</button>
        </div>
      </div>
    </>
  );
};

const backdropStyle: React.CSSProperties = {
  position: 'fixed', inset: 0, background: 'var(--scada-outline)', opacity: 0.5, zIndex: 1000
};

const dialogStyle: React.CSSProperties = {
  position: 'fixed', top: '50%', left: '50%', transform: 'translate(-50%, -50%)',
  zIndex: 1001, width: '620px', maxHeight: '70vh', display: 'flex', flexDirection: 'column',
  background: 'var(--scada-panel)', border: '2px solid var(--scada-outline)', color: 'var(--scada-outline)',
  fontFamily: 'var(--scada-font-ui)', fontSize: 'var(--scada-font-size-base)'
};

const headerStyle: React.CSSProperties = {
  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
  padding: '8px 12px', borderBottom: '1px solid var(--scada-outline)', fontWeight: 'bold'
};

const closeButtonStyle: React.CSSProperties = { background: 'transparent', border: 'none', cursor: 'pointer' };

const tabBarStyle: React.CSSProperties = { display: 'flex', borderBottom: '1px solid var(--scada-outline)' };
const tabBaseStyle: React.CSSProperties = { padding: '6px 16px', cursor: 'pointer' };
const tabActiveStyle: React.CSSProperties = { ...tabBaseStyle, background: 'var(--scada-value-field)', fontWeight: 'bold' };
const tabInactiveStyle: React.CSSProperties = { ...tabBaseStyle };

const bodyStyle: React.CSSProperties = { overflowY: 'auto', flex: 1 };

const tableStyle: React.CSSProperties = { width: '100%', borderCollapse: 'collapse', fontSize: `${FONT_SIZE_BASE}px` };
const thStyle: React.CSSProperties = { textAlign: 'left', borderBottom: '1px solid var(--scada-outline)', padding: '2px 4px' };
const tdStyle: React.CSSProperties = { padding: '2px 4px', borderBottom: '1px solid var(--scada-bevel-dark)' };
const inputStyle: React.CSSProperties = { width: '100%', fontSize: `${FONT_SIZE_BASE}px` };
const errorStyle: React.CSSProperties = { color: COLOR_ALARM, fontSize: `${FONT_SIZE_SMALL}px`, marginTop: '6px' };

const footerStyle: React.CSSProperties = {
  display: 'flex', justifyContent: 'flex-end', gap: '8px', padding: '8px 12px', borderTop: '1px solid var(--scada-outline)'
};
