// feat/multi-screen: several screens in one project - a controller runs
// more than one room, and they are switched, not redrawn.
//
// THE DESIGN, and why it is shaped this way.
//
// The ACTIVE screen's content stays exactly where it has always been:
// the store's own objects/connections/meters/... arrays. Only the
// screens that are NOT on display live in a map, keyed by screen id.
// Switching screens captures the live arrays into that map and loads
// the target's back out.
//
// The alternative - keeping every screen in the map and having the
// canvas read `screens[activeId].objects` - would have been tidier on
// paper and would have touched roughly forty files: every component,
// every slice, every selector that says `objects` today. This way the
// whole feature is one slice plus a tab bar, and nothing that draws,
// selects, edits or validates a screen has to know screens exist at
// all. The cost is one invariant, stated here and enforced in exactly
// one place (screensSlice): the live arrays ARE the active screen, so
// anything that reads all screens must flush the live ones into the map
// first (captureActiveScreen).
//
// Type definitions and pure helpers only.

import type { MeterElement } from '../meter/MeterElement';
import type { SignalPanelElement } from '../elements/SignalPanelElement';
import type { FrameElement } from '../elements/FrameElement';
import type { GroupCommandElement } from '../elements/GroupCommandElement';
import type { SetpointPanelElement } from '../elements/SetpointElement';
import type { WallElement } from '../elements/WallElement';
import type { SynopticConnection, SynopticObject } from '../store/types';
import type { FloorMaterialId } from '../theme/Materials';

/** One screen's identity. Content lives separately - see the header. */
export interface ScreenInfo {
  id: string;
  name: string;
}

/** Everything that belongs to ONE screen. Devices, locations and cards are deliberately absent: those are project-wide registries shared by every screen, which is the entire point of having a registry. */
export interface ScreenContent {
  objects: SynopticObject[];
  connections: SynopticConnection[];
  meters: MeterElement[];
  signalPanels: SignalPanelElement[];
  frames: FrameElement[];
  walls: WallElement[];
  groupCommands: GroupCommandElement[];
  setpointPanels: SetpointPanelElement[];
  /** Per screen, because one controller's plant room and its office are not floored alike. */
  floorMaterial?: FloorMaterialId;
}

export function blankScreenContent(): ScreenContent {
  return {
    objects: [],
    connections: [],
    meters: [],
    signalPanels: [],
    frames: [],
    walls: [],
    groupCommands: [],
    setpointPanels: [],
  };
}

/** A deep copy, so a captured screen can never alias the live arrays it came from - editing screen A after switching to B would otherwise write into A's stored copy as well. */
export function cloneScreenContent(content: ScreenContent): ScreenContent {
  return JSON.parse(JSON.stringify(content));
}

/** A name no other screen is using, derived from `base` ("Ekran", "Ekran 2", ...). */
export function uniqueScreenName(screens: ScreenInfo[], base: string): string {
  const taken = new Set(screens.map(s => s.name.trim().toLowerCase()));
  if (!taken.has(base.trim().toLowerCase())) return base;
  for (let i = 2; i < 1000; i++) {
    const candidate = `${base} ${i}`;
    if (!taken.has(candidate.trim().toLowerCase())) return candidate;
  }
  return `${base} ${Date.now()}`;
}
