/** @vitest-environment jsdom */
// feat/help-system commit 6 - the glossary rendered inside the real
// Help window (the term/definition list, not just the underlying data).

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { useStore } from '../store';
import { HelpWindow } from '../components/HelpWindow';

function resetStore() {
  useStore.setState({ helpLanguage: 'pl' });
}

describe('HelpWindow - glossary (chapter 13)', () => {
  beforeEach(resetStore);
  afterEach(cleanup);

  it('shows glossary terms and their definitions', () => {
    render(<HelpWindow request={{ topicId: 'glossary-all', nonce: 0 }} onClose={() => {}} />);
    expect(screen.getByText('Aparat')).toBeTruthy();
    expect(screen.getByText(/Jednostka konfiguracji zdefiniowana raz/)).toBeTruthy();
  });

  it('clicking a glossary entry\'s link navigates to its topic', () => {
    render(<HelpWindow request={{ topicId: 'glossary-all', nonce: 0 }} onClose={() => {}} />);
    const arrows = screen.getAllByText('→');
    fireEvent.click(arrows[0]);
    // Whichever entry is alphabetically first, the content heading changes
    // away from the glossary's own title (still visible in the left tree,
    // which is why this checks the <h2> heading specifically, not any text).
    expect(screen.queryByRole('heading', { name: '13. Slownik pojec' })).toBeNull();
  });

  it('switching language re-localizes the glossary terms', () => {
    render(<HelpWindow request={{ topicId: 'glossary-all', nonce: 0 }} onClose={() => {}} />);
    expect(screen.getByText('Zacisk')).toBeTruthy();
    fireEvent.change(screen.getByDisplayValue('Polski'), { target: { value: 'en' } });
    expect(screen.getByText('Terminal')).toBeTruthy();
  });
});
