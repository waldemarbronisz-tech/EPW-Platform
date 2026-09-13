import type { SymbolDefinition } from '../SymbolRegistry';
import { cm } from '../../theme/Scale';

// feat/room-plan: the BUDYNEK category - symbols for an architectural
// FLOOR PLAN (a room seen from above), as opposed to every other
// category here, which draws a one-line/process SCHEMATIC.
//
// The two live side by side on purpose. scada.socket and
// electrical.indicator_lamp are the schematic socket and the panel
// signal lamp and stay exactly as they are; these are the plan symbols
// an electrician expects on a room drawing. Neither replaces the other.
//
// SIZES, and the one deliberate distinction between two kinds of them.
//
// Everything is expressed through cm() (theme/Scale.ts: 1 m = 80 px,
// one grid cell = 20 cm), so a dimension in this file reads as the
// dimension it is. But the two groups are NOT treated alike, and that
// is drafting practice rather than a compromise:
//
//   - THINGS THAT OCCUPY SPACE are drawn at true size. A 90 cm door, a
//     120 cm window, a 3 m gate, a 140x80 cm table, a 45 cm chair. You
//     put a chair under that table to see whether it fits, so the
//     drawing has to be able to answer.
//
//   - ELECTRICAL ACCESSORIES are drawn as SYMBOLS, about half again
//     over true size. A ceiling fitting really is 30 cm and a downlight
//     17 cm; drawn at that, next to a 140 cm table, they came out as
//     specks - which is exactly how it was reported. Every electrical
//     plan ever drawn does this: the symbol marks WHERE a fitting is
//     and WHAT it is, and nobody scales a socket off a drawing. The
//     sizes below say so explicitly, in the same cm() units, rather
//     than hiding an arbitrary multiplier.
//
// The one exception inside that second group is the fluorescent
// batten's LENGTH, which stays true at 1.2 m: a batten's length is a
// real layout constraint, it is what a row of them is spaced by, and
// the lighting calculation samples along it (project/Illuminance.ts).
// Only its width is drawn over size.
//
// NO TERMINALS on any of them, and this is the deliberate part: the
// operable ones are driven by their CIRCUIT (SynopticObject.circuit -
// a plain name like 'OBW_SWIATLO_1'), never by a wire touching them.
// Declaring a terminal would put them into NetResolver.ts's geometric
// net model too, giving one symbol two competing ideas of "is it
// energized" - the net's and the circuit's - which is exactly the
// ambiguity this design avoids. A plan is not a wiring diagram: you
// assign a fixture to a circuit, you do not draw the cable to it.
//
// Which of these a circuit can actually switch is declared once, in
// project/CircuitResolver.ts - not inferred from this file.

export const buildingSymbols: Record<string, SymbolDefinition> = {
  // ---- lighting ----------------------------------------------------------
  'building.luminaire': {
    type: 'building.luminaire',
    label: 'Ceiling luminaire',
    category: 'BUILDING',
    // Symbol size - true fitting is about 30 cm. See the header. Kept
    // just under a chair's 45 cm: a fitting symbol that is as big as the
    // furniture stops reading as a symbol and starts reading as an
    // obstruction standing in the room.
    defaultWidth: cm(42),
    defaultHeight: cm(42),
    allowedStates: ['ON', 'OFF'],
    defaultState: 'OFF',
    designationPrefix: 'L',
    resizeRedraws: true
  },
  'building.luminaire_pendant': {
    type: 'building.luminaire_pendant',
    label: 'Pendant luminaire',
    category: 'BUILDING',
    defaultWidth: cm(46),
    defaultHeight: cm(46),
    allowedStates: ['ON', 'OFF'],
    defaultState: 'OFF',
    designationPrefix: 'L',
    resizeRedraws: true
  },
  'building.luminaire_wall': {
    type: 'building.luminaire_wall',
    label: 'Wall light',
    category: 'BUILDING',
    defaultWidth: cm(40),
    defaultHeight: cm(20),
    allowedStates: ['ON', 'OFF'],
    defaultState: 'OFF',
    designationPrefix: 'L',
    resizeRedraws: true
  },
  'building.luminaire_fluorescent': {
    type: 'building.luminaire_fluorescent',
    label: 'Fluorescent luminaire',
    category: 'BUILDING',
    // LENGTH stays true - see the header's own exception - only the
    // width is drawn over size, so the batten still reads as a batten.
    defaultWidth: cm(120),
    defaultHeight: cm(26),
    allowedStates: ['ON', 'OFF'],
    defaultState: 'OFF',
    designationPrefix: 'L',
    resizeRedraws: true
  },
  'building.luminaire_halogen': {
    type: 'building.luminaire_halogen',
    label: 'Halogen spot',
    category: 'BUILDING',
    // True trim is about 17 cm; at that it was a speck on the plan.
    defaultWidth: cm(30),
    defaultHeight: cm(30),
    allowedStates: ['ON', 'OFF'],
    defaultState: 'OFF',
    designationPrefix: 'L',
    resizeRedraws: true
  },

  // ---- power -------------------------------------------------------------
  'building.socket_outlet': {
    type: 'building.socket_outlet',
    label: 'Socket outlet',
    category: 'BUILDING',
    defaultWidth: cm(32),
    defaultHeight: cm(32),
    allowedStates: ['LIVE', 'DEAD'],
    defaultState: 'DEAD',
    designationPrefix: 'G',
    resizeRedraws: true
  },

  // ---- openings ----------------------------------------------------------
  'building.door': {
    type: 'building.door',
    label: 'Door',
    category: 'BUILDING',
    defaultWidth: cm(90),
    defaultHeight: cm(25),
    allowedStates: ['NORMAL'],
    defaultState: 'NORMAL',
    designationPrefix: 'D',
    resizeRedraws: true
  },
  'building.window': {
    type: 'building.window',
    label: 'Window',
    category: 'BUILDING',
    defaultWidth: cm(120),
    defaultHeight: cm(20),
    allowedStates: ['NORMAL'],
    defaultState: 'NORMAL',
    designationPrefix: 'O',
    resizeRedraws: true
  },
  'building.gate': {
    type: 'building.gate',
    label: 'Entrance gate (motorised)',
    category: 'BUILDING',
    defaultWidth: cm(300),
    defaultHeight: cm(30),
    // The one opening that MOVES - it has a drive, so it has a state and
    // belongs on a circuit like any other controlled device.
    allowedStates: ['CLOSED', 'OPEN'],
    defaultState: 'CLOSED',
    designationPrefix: 'B',
    resizeRedraws: true
  },

  // ---- furniture ---------------------------------------------------------
  'building.table': {
    type: 'building.table',
    label: 'Table',
    category: 'BUILDING',
    defaultWidth: cm(140),
    defaultHeight: cm(80),
    allowedStates: ['NORMAL'],
    defaultState: 'NORMAL',
    designationPrefix: 'M',
    resizeRedraws: true
  },
  'building.chair': {
    type: 'building.chair',
    label: 'Chair',
    category: 'BUILDING',
    defaultWidth: cm(45),
    defaultHeight: cm(45),
    allowedStates: ['NORMAL'],
    defaultState: 'NORMAL',
    designationPrefix: 'M',
    resizeRedraws: true
  },
  'building.shelf': {
    type: 'building.shelf',
    label: 'Shelving',
    category: 'BUILDING',
    defaultWidth: cm(80),
    defaultHeight: cm(35),
    allowedStates: ['NORMAL'],
    defaultState: 'NORMAL',
    designationPrefix: 'M',
    resizeRedraws: true
  }
};
