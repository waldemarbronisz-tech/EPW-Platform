// feat/device-list-ui commit 3 - a three-part (card / channel number)
// picker for one ChannelAddress field, restricted to cards of the right
// ChannelKind (DeviceSchema.ts's own CARD.KIND.CHANNEL format) and
// disabling any channel another device already occupies (the `occupied`
// map - DeviceRegistryQueries.getOccupiedChannels, called with the
// current device's own id excluded so editing a device never reports its
// own already-saved channel as taken).
//
// Uses DeviceValidation.ts's own parseChannelAddress to read the current
// value back out - never re-implements address parsing here.

import React, { useState } from 'react';
import type { CardEntry, ChannelAddress, ChannelKind } from '../project/DeviceSchema';
import { parseChannelAddress } from '../project/DeviceValidation';
import { AddCardDialog } from './AddCardDialog';

export interface ChannelAddressPickerProps {
  value: ChannelAddress | undefined;
  onChange: (addr: ChannelAddress | undefined) => void;
  expectedKind: ChannelKind;
  cards: CardEntry[];
  occupied: Map<string, { deviceId: string; field: string }>;
  // True for a genuinely optional field (extraInputs.diFault,
  // feedbackInput) - shows an enable checkbox that clears the value
  // entirely when unchecked. Fields whose presence is driven by another
  // choice (feedback.mode, command.outputCount) are shown/hidden by the
  // parent form instead - never pass allowEmpty for those.
  allowEmpty?: boolean;
}

export const ChannelAddressPicker: React.FC<ChannelAddressPickerProps> = ({ value, onChange, expectedKind, cards, occupied, allowEmpty }) => {
  // fix/inline-device-creation commit 2: "+ Karta" opens AddCardDialog
  // right here, at whichever channel field needed a card that does not
  // exist yet - see that dialog's own header for why channelKind is
  // fixed to expectedKind rather than a free choice.
  const [showAddCard, setShowAddCard] = useState(false);
  const matchingCards = cards.filter(c => c.channelKind === expectedKind);
  const parsed = value ? parseChannelAddress(value) : null;
  // Empirical fix (KROK 2 of this task's own manual verification): a
  // brand-new required field defaults internally to the first matching
  // card/channel 1 so a single click on either dropdown already emits a
  // real address - but showing that phantom choice as already SELECTED,
  // before the user ever touched it, looked exactly like a filled field
  // while the actual stored value was still '' (only the validation
  // text below gave away that it was not). hasValue is what the two
  // <select>s below actually display; the phantom defaults still decide
  // what a first interaction emits.
  const hasValue = !!parsed;
  const selectedCard = parsed?.card ?? matchingCards[0]?.id ?? '';
  const selectedChannel = parsed?.channel ?? 1;
  const card = matchingCards.find(c => c.id === selectedCard);

  const emit = (cardId: string, channel: number) => {
    if (!cardId) { onChange(undefined); return; }
    onChange(`${cardId}.${expectedKind}.${channel}`);
  };

  // fix/inline-device-creation commit 2, mandatory test 8: a
  // brand-new card has no occupied channels yet, so channel 1 is always
  // free - selecting it immediately, the same way choosing an existing
  // card from the first <select> above would, needs no extra lookup.
  const handleCardAdded = (cardId: string) => {
    setShowAddCard(false);
    emit(cardId, 1);
  };

  const addCardButton = (
    <button type="button" onClick={() => setShowAddCard(true)} title={`Add a new ${expectedKind} card`}>+ Card</button>
  );

  const selects = (
    <>
      <select value={hasValue ? selectedCard : ''} onChange={e => emit(e.target.value, selectedChannel)} style={selectStyle}>
        {matchingCards.length === 0 && <option value="">(no {expectedKind} cards)</option>}
        {!hasValue && matchingCards.length > 0 && <option value="">-- select --</option>}
        {matchingCards.map(c => <option key={c.id} value={c.id}>{c.id}</option>)}
      </select>
      <select value={hasValue ? selectedChannel : ''} onChange={e => emit(selectedCard, Number(e.target.value))} style={selectStyle} disabled={!card}>
        {!hasValue && card && <option value="">-- select --</option>}
        {card && Array.from({ length: card.channelCount }, (_, i) => i + 1).map(n => {
          const key = `${selectedCard}.${expectedKind}.${n}`;
          const usedBy = occupied.get(key);
          return (
            <option key={n} value={n} disabled={!!usedBy}>
              {n}{usedBy ? ` (used by: ${usedBy.deviceId})` : ''}
            </option>
          );
        })}
      </select>
      {addCardButton}
      {showAddCard && (
        <AddCardDialog expectedKind={expectedKind} onAdded={handleCardAdded} onCancel={() => setShowAddCard(false)} />
      )}
    </>
  );

  if (!allowEmpty) {
    return <div style={rowStyle}>{selects}</div>;
  }

  return (
    <div style={rowStyle}>
      <input
        type="checkbox"
        checked={!!value}
        onChange={e => e.target.checked ? emit(selectedCard, selectedChannel) : onChange(undefined)}
      />
      {value !== undefined && selects}
    </div>
  );
};

const rowStyle: React.CSSProperties = { display: 'flex', gap: '4px', alignItems: 'center' };
const selectStyle: React.CSSProperties = { fontSize: 'var(--scada-font-size-base)' };
