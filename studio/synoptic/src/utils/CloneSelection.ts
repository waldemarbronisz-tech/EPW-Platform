// feat/editing-and-signal-panel commit 2: copy/paste/duplicate, shared
// by store.ts's copySelected+paste and duplicateSelected. Pure,
// Konva-free (same convention as GridSnap.ts/Terminals.ts/
// WireDrawing.ts) - takes plain arrays, returns plain arrays, no
// Zustand involved, so it is testable without a store at all.
//
// A connection references nothing by id in the node-based wiring model
// - it is a free polyline that happens to touch a terminal
// geometrically (see NetResolver.ts). That is what makes cloning a
// connected fragment trivial and correct with no relinking step at
// all: shift a copied object's x/y and a copied connection's points by
// the EXACT SAME offset, and the copy's own wire still touches the
// copy's own terminals (translation does not change relative
// geometry) - while the original is left exactly where it was, so the
// copy touches nothing of the original's.

import type { SynopticObject, SynopticConnection } from '../store';
import type { MeterElement } from '../meter/MeterElement';
import type { SignalPanelElement } from '../elements/SignalPanelElement';
import type { FrameElement } from '../elements/FrameElement';
import type { GroupCommandElement } from '../elements/GroupCommandElement';
import type { SetpointPanelElement } from '../elements/SetpointElement';

export interface ClonedSelection {
  objects: SynopticObject[];
  meters: MeterElement[];
  signalPanels: SignalPanelElement[];
  frames: FrameElement[];
  groupCommands: GroupCommandElement[];
  setpointPanels: SetpointPanelElement[];
  connections: SynopticConnection[];
  objectIds: string[];
  meterIds: string[];
  signalPanelIds: string[];
  frameIds: string[];
  groupCommandIds: string[];
  setpointPanelIds: string[];
  connectionIds: string[];
}

/**
 * Clones a selection (objects, meters, signal panels, frames,
 * connections - any may be empty) offset by (dx, dy), with fresh ids
 * throughout. Deep-clones every source item first (JSON round-trip,
 * the same technique the store's own clipboard already used) so the
 * result shares no reference with its source - mutating a pasted
 * object must never silently mutate the thing it was copied from. A
 * signal panel or a frame clones exactly like a meter (id + x/y
 * offset, nothing else to touch) - all three are "point elements" with
 * no internal geometry of their own to shift, unlike a connection's
 * points array.
 */
export function cloneSelectionWithOffset(
  objects: SynopticObject[],
  meters: MeterElement[],
  signalPanels: SignalPanelElement[],
  frames: FrameElement[],
  connections: SynopticConnection[],
  dx: number,
  dy: number,
  makeId: () => string,
  groupCommands: GroupCommandElement[] = [],
  setpointPanels: SetpointPanelElement[] = []
): ClonedSelection {
  const clonedObjects: SynopticObject[] = JSON.parse(JSON.stringify(objects));
  const clonedMeters: MeterElement[] = JSON.parse(JSON.stringify(meters));
  const clonedSignalPanels: SignalPanelElement[] = JSON.parse(JSON.stringify(signalPanels));
  const clonedFrames: FrameElement[] = JSON.parse(JSON.stringify(frames));
  const clonedGroupCommands: GroupCommandElement[] = JSON.parse(JSON.stringify(groupCommands));
  const clonedSetpointPanels: SetpointPanelElement[] = JSON.parse(JSON.stringify(setpointPanels));
  const clonedConnections: SynopticConnection[] = JSON.parse(JSON.stringify(connections));

  const newObjects = clonedObjects.map(obj => ({ ...obj, id: makeId(), x: obj.x + dx, y: obj.y + dy }));
  const newMeters = clonedMeters.map(m => ({ ...m, id: makeId(), x: m.x + dx, y: m.y + dy }));
  const newSignalPanels = clonedSignalPanels.map(p => ({ ...p, id: makeId(), x: p.x + dx, y: p.y + dy }));
  const newFrames = clonedFrames.map(f => ({ ...f, id: makeId(), x: f.x + dx, y: f.y + dy }));
  const newGroupCommands = clonedGroupCommands.map(g => ({ ...g, id: makeId(), x: g.x + dx, y: g.y + dy }));
  const newSetpointPanels = clonedSetpointPanels.map(p => ({ ...p, id: makeId(), x: p.x + dx, y: p.y + dy }));
  const newConnections = clonedConnections.map(conn => ({
    ...conn,
    id: makeId(),
    points: conn.points.map(p => ({ x: p.x + dx, y: p.y + dy }))
  }));

  return {
    objects: newObjects,
    meters: newMeters,
    signalPanels: newSignalPanels,
    frames: newFrames,
    groupCommands: newGroupCommands,
    setpointPanels: newSetpointPanels,
    connections: newConnections,
    objectIds: newObjects.map(o => o.id),
    meterIds: newMeters.map(m => m.id),
    signalPanelIds: newSignalPanels.map(p => p.id),
    frameIds: newFrames.map(f => f.id),
    groupCommandIds: newGroupCommands.map(g => g.id),
    setpointPanelIds: newSetpointPanels.map(p => p.id),
    connectionIds: newConnections.map(c => c.id)
  };
}
