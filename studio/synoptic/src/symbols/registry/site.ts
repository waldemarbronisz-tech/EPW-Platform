// feat/site-objects-2d: the TEREN (site object) category. Every entry's
// declared size is 128x96 - NOT docs/EPW_rysunki_referencja.py's own
// literal W,H=160,120 (that describes the reference drawing's own
// proportions, 4:3, not the symbol's size in this library). 120 is not
// an EVEN GRID_SIZE multiple (terminal-centering.test.ts's own
// pre-existing invariant, feat/editing-and-signal-panel commit 1), so
// a symbol declared at 160x120 could never get a real, grid-aligned
// edge-midpoint terminal on its own top/bottom edge. 128x96 is the
// identical 4:3 ratio (128/96 = 160/120), reached by drawing every
// shape at the reference's own literal 160x120 coordinates and
// wrapping that in one SITE_CANVAS_SCALE (0.8) Group - see
// ScadaTheme.ts's own comment on that constant for the full reasoning,
// found live and resolved with the user (raport.md). Not meant to be
// freely resized the way an ordinary schematic symbol might be -
// trawa/droga, the two SURFACES, are the deliberate exception, see
// their own commit 4 registry entries.
//
// Terminal placement: every non-surface object gets terminals at
// whichever edge midpoint its own real-world connection point sits
// nearest - the electrical feed for a building/fixture/gate, the pipe
// for anything water-related. Both surfaces (grass, concrete road)
// have NONE at all - this task's own commit 4 spec is explicit that a
// surface has nothing to wire up ("Nie maja zaciskow"), a deliberate,
// narrower exception to this file's own general "every object gets
// terminals" rule.
import type { SymbolDefinition } from '../SymbolRegistry';

export const siteSymbols: Record<string, SymbolDefinition> = {
  'site.house': {
    type: 'site.house',
    label: 'House',
    category: 'SITE',
    defaultWidth: 128,
    defaultHeight: 96,
    allowedStates: ['ON', 'OFF'],
    defaultState: 'OFF',
    terminals: [{ id: 'ZASILANIE', side: 'BOTTOM', medium: 'ELECTRICAL' }]
  },
  'site.warehouse': {
    type: 'site.warehouse',
    label: 'Warehouse',
    category: 'SITE',
    defaultWidth: 128,
    defaultHeight: 96,
    allowedStates: ['ON', 'OFF'],
    defaultState: 'OFF',
    terminals: [{ id: 'ZASILANIE', side: 'BOTTOM', medium: 'ELECTRICAL' }]
  },
  'site.sliding_gate': {
    type: 'site.sliding_gate',
    label: 'Sliding Gate',
    category: 'SITE',
    defaultWidth: 128,
    defaultHeight: 96,
    allowedStates: ['CLOSED', 'MOVING', 'OPEN'],
    defaultState: 'CLOSED',
    terminals: [{ id: 'ZASILANIE', side: 'BOTTOM', medium: 'ELECTRICAL' }]
  },
  // Commit 4 - the two SURFACES. Both isSurface:true (background pass,
  // Canvas.tsx) and terminals: [] (WYMAGANIA WSPOLNE: "Nie maja
  // zaciskow" - explicit empty list, not merely omitted, same as every
  // other entry here declaring its own terminals rather than leaving
  // the field undefined). defaultWidth/defaultHeight are only a
  // starting point, not a fixed drawing size the way they are for the
  // other 14 - a surface is explicitly meant to be resized afterward
  // (GrassSymbol.tsx/ConcreteRoadSymbol.tsx's own header comments).
  'site.grass': {
    type: 'site.grass',
    label: 'Grass',
    category: 'SITE',
    defaultWidth: 128,
    defaultHeight: 96,
    allowedStates: ['ON', 'OFF'],
    defaultState: 'OFF',
    terminals: [],
    isSurface: true
  },
  'site.concrete_road': {
    type: 'site.concrete_road',
    label: 'Concrete Road',
    category: 'SITE',
    defaultWidth: 192,
    defaultHeight: 96,
    allowedStates: [],
    defaultState: '',
    terminals: [],
    isSurface: true
  },

  // fix/hydraulic-connections commit 7: TEREN used to also hold
  // twenty-three electrical/water/instrumentation objects - eleven from
  // feat/site-objects-2d, twelve from feat/water-management - registered
  // here by when they were built, not what they are. All twenty-three
  // relocated to registry/electrical.ts (7), registry/water.ts (15) and
  // registry/instrumentation.ts (1) respectively (see each of those
  // files' own header comment on this same commit for the full list and
  // reasoning). TEREN now holds exactly the five objects that are
  // genuinely site-layout infrastructure: the house, the warehouse, the
  // sliding gate, and the two surfaces above.
};
