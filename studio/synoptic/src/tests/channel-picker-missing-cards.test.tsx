/** @vitest-environment jsdom */
// User report ("gdy dodajemy cos, co wymaga fizycznego wejscia lub
// wyjscia, a nie ma kart - niech wyskoczy informacja"): the Synoptic
// side already refused to invent an address when no card of the needed
// kind exists, but it said so only as "(no DI cards)" INSIDE the closed
// dropdown - invisible until you opened it. The notice is now on the
// field itself, next to the "+ Card" button that fixes it.

import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { ChannelAddressPicker } from '../components/ChannelAddressPicker';
import type { CardEntry } from '../project/DeviceSchema';

const DI_CARD: CardEntry = { id: 'ELA1', model: 'ELA01', channelKind: 'DI', channelCount: 16 };
const DO_CARD: CardEntry = { id: 'ADA1', model: 'ADA01', channelKind: 'DO', channelCount: 16 };

function renderPicker(cards: CardEntry[], props: Partial<React.ComponentProps<typeof ChannelAddressPicker>> = {}) {
  return render(
    <ChannelAddressPicker
      value={undefined}
      onChange={() => {}}
      expectedKind="DI"
      cards={cards}
      occupied={new Map()}
      {...props}
    />
  );
}

describe('ChannelAddressPicker - no card of the needed kind', () => {
  afterEach(cleanup);

  it('says which kind is missing, on the field itself', () => {
    renderPicker([]);
    expect(screen.getByText(/No DI cards in this project/)).toBeTruthy();
  });

  it('points at the button that fixes it', () => {
    renderPicker([]);
    expect(screen.getByText(/add one with "\+ Card"/)).toBeTruthy();
    expect(screen.getByRole('button', { name: '+ Card' })).toBeTruthy();
  });

  it('a card of a DIFFERENT kind is still no card for this field', () => {
    renderPicker([DO_CARD]);
    expect(screen.getByText(/No DI cards in this project/)).toBeTruthy();
  });

  it('stays quiet once a card of the right kind exists', () => {
    renderPicker([DI_CARD]);
    expect(screen.queryByText(/No DI cards in this project/)).toBeNull();
  });

  it('an optional field says nothing until it is switched on', () => {
    // allowEmpty renders only a checkbox until the field is enabled -
    // warning about a missing card for a field nobody asked for would be
    // noise, not help.
    const { rerender } = renderPicker([], { allowEmpty: true });
    expect(screen.queryByText(/No DI cards in this project/)).toBeNull();

    rerender(
      <ChannelAddressPicker
        value={'ELA1.DI.1'}
        onChange={() => {}}
        expectedKind="DI"
        cards={[]}
        occupied={new Map()}
        allowEmpty
      />
    );
    expect(screen.getByText(/No DI cards in this project/)).toBeTruthy();
  });
});
