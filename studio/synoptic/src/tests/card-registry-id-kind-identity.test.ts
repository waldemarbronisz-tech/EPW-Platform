// A CardEntry is identified by (id, channelKind), not by id alone: one
// physical module with several kinds (Studio's Card.channel_kinds,
// flattened by the bridge) is several entries sharing an id. The store's
// updateCard/deleteCard used to match on id only, so editing or deleting
// the AI entry of ELA1 silently overwrote/removed its DI sibling too -
// and getChannelUsagesForCard blocked deleting the AI entry because a
// device was wired to a DI channel.
import { describe, it, expect, beforeEach } from 'vitest';
import { useStore } from '../store';
import type { CardEntry, SignalDevice } from '../project/DeviceSchema';
import { getChannelUsagesForCard } from '../project/DeviceRegistryQueries';

const DI: CardEntry = { id: 'ELA1', model: 'ELA01', channelKind: 'DI', channelCount: 16 };
const AI: CardEntry = { id: 'ELA1', model: 'ELA01', channelKind: 'AI', channelCount: 8 };

describe('card registry: (id, kind) is the identity of a CardEntry', () => {
  beforeEach(() => {
    useStore.setState({ cards: [], devices: [], locations: [] });
    useStore.getState().addCard(DI);
    useStore.getState().addCard(AI);
  });

  it('deleteCard removes only the entry of that kind', () => {
    useStore.getState().deleteCard('ELA1', 'AI');
    expect(useStore.getState().cards).toEqual([DI]);
  });

  it('updateCard rewrites only the entry of that kind', () => {
    useStore.getState().updateCard('ELA1', 'AI', { ...AI, channelCount: 4 });
    expect(useStore.getState().cards).toEqual([DI, { ...AI, channelCount: 4 }]);
  });

  it('usage of a card can be asked per kind, so a DI wiring does not pin the AI entry', () => {
    const device: SignalDevice = {
      id: 'KOT_Q1', designation: '-Q1', name: 'Q1', behavior: 'SIGNAL', kind: 'level_switch',
      publishToHa: false, feedback: { di: 'ELA1.DI.3', invert: false }, alarmState: 'HIGH', debounceMs: 50,
    };
    const devices = [device];
    expect(getChannelUsagesForCard(devices, 'ELA1', 'DI')).toHaveLength(1);
    expect(getChannelUsagesForCard(devices, 'ELA1', 'AI')).toHaveLength(0);
    expect(getChannelUsagesForCard(devices, 'ELA1')).toHaveLength(1); // no kind: the whole id, as before
  });
});
