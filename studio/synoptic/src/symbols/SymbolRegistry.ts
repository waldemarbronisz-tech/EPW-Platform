// Legacy port model - kept only so old code (ConnectionService.ts,
// GeometryUtils.ts, the pre-node-based-wiring symbol registries that
// still declare it) keeps compiling. No longer read by the live canvas
// wiring path: Terminal/terminals below replaced it for that purpose.
export interface ConnectionPoint {
  id: string;
  x: number; // percentage (0 to 1) relative to width
  y: number; // percentage (0 to 1) relative to height
  domain?: 'electrical' | 'water' | 'hvac' | 'data' | 'control';
  medium?: string;
  direction?: 'in' | 'out' | 'bidirectional' | 'passive';
  multiplicity?: 'single' | 'multiple';
}

// Node-based wiring model: a symbol has terminals, not ports. Each
// terminal sits at a fixed LOCAL point (from the symbol's own top-left,
// same origin obj.x/obj.y always means), which MUST be a multiple of
// GRID_SIZE - a wire ending exactly on that world point is connected,
// no id-matching involved (see NetResolver.ts). Resolved shape - what
// getObjectTerminals (utils/Terminals.ts) hands back, x/y already
// computed. A symbol's own registry entry never declares one of these
// directly - see TerminalSpec below.
export interface Terminal {
  id: string;
  x: number; // local px from top-left, multiple of GRID_SIZE
  y: number; // local px from top-left, multiple of GRID_SIZE
  medium: 'ELECTRICAL' | 'WATER' | 'VENTILATION';
}

// feat/editing-and-signal-panel commit 1: a terminal lies ALWAYS on the
// middle of a symbol's edge - so a symbol's own registry entry only
// ever needs to say WHICH edge, never a raw x/y. utils/Terminals.ts's
// getObjectTerminals turns a TerminalSpec into a real Terminal (x/y
// resolved from the object's own current width/height) at read time.
export type TerminalSide = 'TOP' | 'BOTTOM' | 'LEFT' | 'RIGHT';

export interface TerminalSpec {
  id: string;
  side: TerminalSide;
  medium: 'ELECTRICAL' | 'WATER' | 'VENTILATION';
}

export interface SymbolDefinition {
  type: string;
  label: string;
  category: string;
  defaultWidth: number;
  defaultHeight: number;
  allowedStates: string[];
  defaultState: string;
  connectionPoints?: ConnectionPoint[];
  terminals?: TerminalSpec[];
  isLine?: boolean;
  designationPrefix?: string;
  supportsDynamicPorts?: boolean;
  // feat/site-objects-2d commit 4: a SURFACE (trawa/droga) - drawn in
  // its own background pass in Canvas.tsx, below every wire and
  // ordinary symbol (WYMAGANIA WSPOLNE's own "warstwa tla", mandatory
  // test 9) - the project's own frame element (its own, separate
  // elements/ file, deliberately never referenced from this registry -
  // see frame-element.test.ts's own decoupling check) already draws
  // first in that same position for the same "background graphic" reason;
  // this flag gets a site object the identical draw-order treatment
  // while staying a real object (not a separate array) so it still
  // gets everything an ordinary symbol gets for free: selection, move,
  // copy, 90-deg rotate, Aparat/device linkage. Adjustable size is not
  // a new mechanism either - the object selection/resize handle already
  // resizes ANY selected object unconditionally (Canvas.tsx); a
  // surface's own component just reads that real size back out instead
  // of drawing at a fixed reference size (see GrassSymbol.tsx's own
  // header comment for the how/why).
  isSurface?: boolean;
  // Object Library trim: symbol stays fully defined and placeable by an
  // already-saved project (old objects of this type still render,
  // still keep their terminals), it just does not appear as a draggable
  // entry in the Toolbox any more. Flip back to expose it again - one
  // line, no file touched.
  hiddenFromLibrary?: boolean;
}

import { electricalSymbols } from './registry/electrical';
import { waterSymbols } from './registry/water';
import { hvacSymbols } from './registry/hvac';
import { automationSymbols } from './registry/automation';
import { instrumentationSymbols } from './registry/instrumentation';
import { measurementsSymbols } from './registry/measurements';
import { graphicsSymbols } from './registry/graphics';
import { scadaSymbols } from './registry/scada';
import { siteSymbols } from './registry/site';

export const SYMBOL_REGISTRY: Record<string, SymbolDefinition> = {
  ...electricalSymbols,
  ...waterSymbols,
  ...hvacSymbols,
  ...automationSymbols,
  ...instrumentationSymbols,
  ...measurementsSymbols,
  ...graphicsSymbols,
  ...scadaSymbols,
  ...siteSymbols
};

export const getSymbolDefinition = (type: string): SymbolDefinition | undefined => {
  return SYMBOL_REGISTRY[type];
};

// fix/hydraulic-connections commit 7: the Object Library's own folder
// order, top to bottom - an explicit list, not however SYMBOL_REGISTRY's
// own import-merge order happens to first encounter each category
// (that order does not match this task's own requested sequence at
// all: SCADA is merged in before TEREN, and Automation right after
// Water, neither of which belongs where this list puts it). Any
// category not named here - none exist today, but a future one might,
// before its own entry gets added here - is appended afterward, in
// whatever order it was first encountered, so it is never silently
// dropped from the library.
const CATEGORY_DISPLAY_ORDER = ['Electrical', 'Water', 'HVAC', 'Instrumentation', 'SITE', 'SCADA', 'Automation'];

// Only what the Object Library should show - getSymbolDefinition above
// stays unfiltered, since an already-placed object of a hidden type
// still needs its full definition (label, terminals, rendering) to work.
export const getSymbolsByCategory = () => {
  const categories: Record<string, SymbolDefinition[]> = {};
  Object.values(SYMBOL_REGISTRY).forEach(def => {
    if (def.hiddenFromLibrary) return;
    if (!categories[def.category]) {
      categories[def.category] = [];
    }
    categories[def.category].push(def);
  });

  const ordered: Record<string, SymbolDefinition[]> = {};
  for (const name of CATEGORY_DISPLAY_ORDER) {
    if (categories[name]) ordered[name] = categories[name];
  }
  for (const name of Object.keys(categories)) {
    if (!ordered[name]) ordered[name] = categories[name];
  }
  return ordered;
};
