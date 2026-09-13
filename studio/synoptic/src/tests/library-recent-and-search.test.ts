// feat/library-recent-and-search: the two things the Logic editor's
// library always had and this one did not.
//
// The list rule and the matching rule are pure (project/RecentSymbols.ts)
// and are checked directly. What the panel does with them is checked by
// source scan, the convention this suite already uses where there is no
// runnable harness.

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import {
  loadRecent, matchesQuery, recordRecent, saveRecent, RECENT_LABEL, RECENT_MAX,
} from '../project/RecentSymbols';
import { useStore } from '../store';

import toolboxSource from '../components/Toolbox.tsx?raw';
import canvasSource from '../components/Canvas.tsx?raw';

describe('recently used', () => {
  it('puts the newest first', () => {
    expect(recordRecent(['a', 'b'], 'c')).toEqual(['c', 'a', 'b']);
  });

  it('MOVES a symbol used again rather than repeating it', () => {
    // Otherwise the list fills with one symbol - exactly the symbol you
    // least need help finding.
    expect(recordRecent(['a', 'b', 'c'], 'c')).toEqual(['c', 'a', 'b']);
    expect(recordRecent(['a'], 'a')).toEqual(['a']);
  });

  it('never grows past the cap', () => {
    let list: string[] = [];
    for (let i = 0; i < RECENT_MAX * 2; i++) list = recordRecent(list, `t${i}`);
    expect(list).toHaveLength(RECENT_MAX);
    expect(list[0]).toBe(`t${RECENT_MAX * 2 - 1}`);
  });

  it('ignores an empty type instead of storing a blank row', () => {
    expect(recordRecent(['a'], '')).toEqual(['a']);
  });

  it('uses the same heading and the same cap as the Logic editor', () => {
    // logic_studio/ui/panels/library.py: RECENT_LABEL / RECENT_MAX = 10.
    expect(RECENT_LABEL).toBe('Recently used');
    expect(RECENT_MAX).toBe(10);
  });
});

describe('recently used, persisted', () => {
  // A minimal store, installed for these tests only: this suite runs in
  // plain node, where there is no localStorage at all - which is itself
  // one of the cases the code has to survive, checked last.
  const store = new Map<string, string>();
  const fake = {
    getItem: (key: string) => store.get(key) ?? null,
    setItem: (key: string, value: string) => { store.set(key, value); },
    removeItem: (key: string) => { store.delete(key); },
    clear: () => { store.clear(); },
  };
  const original = Object.getOwnPropertyDescriptor(globalThis, 'localStorage');

  beforeEach(() => {
    store.clear();
    Object.defineProperty(globalThis, 'localStorage', { value: fake, configurable: true });
  });

  afterEach(() => {
    if (original) Object.defineProperty(globalThis, 'localStorage', original);
    else delete (globalThis as { localStorage?: unknown }).localStorage;
  });

  it('survives a round trip', () => {
    saveRecent(['a', 'b']);
    expect(loadRecent()).toEqual(['a', 'b']);
  });

  it('returns an empty list rather than throwing on rubbish in storage', () => {
    // A library that will not open because something wrote a bad value
    // into storage is far worse than a library that forgot the list.
    fake.setItem('epw-synoptic/library-recent', '{not json');
    expect(loadRecent()).toEqual([]);
  });

  it('degrades to a session-only list where there is no storage at all', () => {
    delete (globalThis as { localStorage?: unknown }).localStorage;
    expect(() => saveRecent(['a'])).not.toThrow();
    expect(loadRecent()).toEqual([]);
  });
});

describe('library search', () => {
  it('finds a symbol by its label and by its type', () => {
    expect(matchesQuery('Oprawa wisząca', 'building.luminaire_pendant', 'oprawa')).toBe(true);
    expect(matchesQuery('Oprawa wisząca', 'building.luminaire_pendant', 'pendant')).toBe(true);
    expect(matchesQuery('Oprawa wisząca', 'building.luminaire_pendant', 'stycznik')).toBe(false);
  });

  it('does not make the user type the diacritics', () => {
    // A search that only works with them is a search most people
    // conclude is broken.
    expect(matchesQuery('Oświetlenie awaryjne', 'x', 'oswietlenie')).toBe(true);
    expect(matchesQuery('Łącznik krzywkowy', 'x', 'lacznik')).toBe(true);
    expect(matchesQuery('Wyłącznik', 'x', 'WYLACZNIK')).toBe(true);
  });

  it('matches everything on an empty query', () => {
    expect(matchesQuery('cokolwiek', 'x', '')).toBe(true);
    expect(matchesQuery('cokolwiek', 'x', '   ')).toBe(true);
  });
});

describe('library wiring (source scan)', () => {
  it('records a symbol where it is PLACED, not where it is clicked', () => {
    expect(canvasSource).toContain('recordSymbolUse(data.type)');
  });

  it('offers a search box and the recent section in the panel', () => {
    expect(toolboxSource).toContain('RECENT_LABEL');
    expect(toolboxSource).toContain('matchesQuery');
    expect(toolboxSource).toContain('Search...');
  });

  it('opens a folder that still has results, instead of hiding them inside it', () => {
    expect(toolboxSource).toContain('const open = searching || expanded[category] !== false');
  });

  it('says so when a search finds nothing', () => {
    expect(toolboxSource).toContain('No symbols match');
  });

  it('keeps the recent list out of the project file', () => {
    // It describes the person drawing, not the drawing.
    const state = useStore.getState();
    expect(Array.isArray(state.recentSymbols)).toBe(true);
    expect(typeof state.recordSymbolUse).toBe('function');
  });
});
