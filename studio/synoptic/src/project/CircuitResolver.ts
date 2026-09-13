// feat/room-plan: circuits (obwody). Pure functions only, no store
// dependency - takes a plain objects array, returns plain data, exactly
// like NetResolver.ts next door.
//
// A circuit is a NAME, not a geometry. Every object carrying the same
// SynopticObject.circuit string is one circuit and switches as one.
// That is the whole model, and it is deliberately separate from
// NetResolver.ts's geometric nets:
//
//   - A net answers "what is physically joined to what", derived from
//     wires touching terminals. It belongs to a one-line SCHEMATIC.
//   - A circuit answers "what does this switch turn on", declared by
//     the user. It belongs to a floor PLAN, where nobody draws the
//     cable to each luminaire.
//
// The two never interact: plan symbols (registry/building.ts) have no
// terminals at all, so they are not on any net, and schematic symbols
// are not normally given a circuit name. Nothing here reads or writes
// a connection.

import type { SynopticObject } from '../store';

/** The ON/OFF pair a given symbol type uses for its own preview state. Both plan symbols are two-state; the pair differs only in vocabulary (a luminaire is ON/OFF, a socket is LIVE/DEAD), so the mapping lives here rather than being guessed at each call site. */
const CIRCUIT_STATES: Record<string, { on: string; off: string }> = {
  'building.luminaire': { on: 'ON', off: 'OFF' },
  'building.luminaire_pendant': { on: 'ON', off: 'OFF' },
  'building.luminaire_wall': { on: 'ON', off: 'OFF' },
  'building.luminaire_fluorescent': { on: 'ON', off: 'OFF' },
  'building.luminaire_halogen': { on: 'ON', off: 'OFF' },
  'building.socket_outlet': { on: 'LIVE', off: 'DEAD' },
  // The powered gate: its drive is switched exactly like a lighting
  // circuit, from the same click and through the same controller
  // output, so it belongs in this table rather than in a mechanism of
  // its own.
  'building.gate': { on: 'OPEN', off: 'CLOSED' },
};
// Furniture and the passive openings (table/chair/shelf/door/window)
// are deliberately absent: they are graphics with no state at all, so
// a circuit click must pass straight over them even when one happens
// to carry a circuit name copied along with a duplicated object.

/** Whether this object's type is one a circuit click can switch at all. Anything else on the canvas is left completely untouched by every function here, even if it happens to carry a circuit name. */
export function isCircuitOperable(type: string): boolean {
  return Object.prototype.hasOwnProperty.call(CIRCUIT_STATES, type);
}

/** Normalizes a circuit name for comparison: trimmed, case-insensitive. 'obw_1', 'OBW_1' and ' OBW_1 ' are the same circuit - a user typing the same name twice in two different cases means the same thing, and a plan that silently split into two circuits over a capital letter would be a nasty bug to chase. The ORIGINAL string is what stays stored and displayed; this is only ever used to group. */
export function normalizeCircuitName(name: string | undefined): string {
  return (name ?? '').trim().toUpperCase();
}

/** Every distinct circuit name present on the given objects, in first-seen order, with the original (non-normalized) spelling of its first occurrence. Objects with no circuit are skipped. */
export function listCircuits(objects: SynopticObject[]): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const obj of objects) {
    const key = normalizeCircuitName(obj.circuit);
    if (!key || seen.has(key)) continue;
    seen.add(key);
    result.push((obj.circuit ?? '').trim());
  }
  return result;
}

/** Every operable object on one circuit. Empty for an empty/blank name - "no circuit" is never a circuit that can be switched, otherwise one click would switch every unassigned fixture on the screen at once. */
export function objectsInCircuit(objects: SynopticObject[], circuit: string | undefined): SynopticObject[] {
  const key = normalizeCircuitName(circuit);
  if (!key) return [];
  return objects.filter(o => isCircuitOperable(o.type) && normalizeCircuitName(o.circuit) === key);
}

/** Whether a circuit currently counts as ON. A circuit is ON when ANY of its objects is on - so a circuit left in a mixed state (hand-edited in Properties, or half of it placed later) resolves to ON, and the next click therefore turns the whole thing OFF. Switching always converges the circuit to one state rather than flipping each object independently, which would leave a mixed circuit mixed forever. */
export function isCircuitOn(objects: SynopticObject[], circuit: string | undefined): boolean {
  return objectsInCircuit(objects, circuit).some(o => {
    const states = CIRCUIT_STATES[o.type];
    return o.editor?.preview_state === states.on;
  });
}

/** The updates that switch a whole circuit to `on`, in the shape updateObjects() already takes. Every object gets the ON/OFF value of ITS OWN type, so a circuit mixing luminaires and sockets sets each to its own correct vocabulary. Returns an empty array for an unknown/blank circuit - never throws. */
export function setCircuitUpdates(
  objects: SynopticObject[],
  circuit: string | undefined,
  on: boolean
): { id: string; updates: Partial<SynopticObject> }[] {
  return objectsInCircuit(objects, circuit).map(o => {
    const states = CIRCUIT_STATES[o.type];
    return {
      id: o.id,
      updates: {
        // Spread the existing editor block rather than replacing it:
        // preview_value/unit/format live there too and must survive a
        // circuit switch untouched.
        editor: { ...o.editor, preview_state: on ? states.on : states.off },
      },
    };
  });
}

/** The updates that flip a whole circuit from wherever it is now. The one function the canvas click actually calls. */
export function toggleCircuitUpdates(
  objects: SynopticObject[],
  circuit: string | undefined
): { id: string; updates: Partial<SynopticObject> }[] {
  return setCircuitUpdates(objects, circuit, !isCircuitOn(objects, circuit));
}

/** Whether one plan object is on, by its own type's vocabulary. False for anything that is not circuit-operable. */
export function isObjectOn(obj: SynopticObject): boolean {
  const states = CIRCUIT_STATES[obj.type];
  return !!states && obj.editor?.preview_state === states.on;
}

/** The update that switches ONE plan object - a fixture simulated without a circuit. Empty for anything not circuit-operable. */
export function setObjectUpdates(obj: SynopticObject, on: boolean): { id: string; updates: Partial<SynopticObject> }[] {
  const states = CIRCUIT_STATES[obj.type];
  if (!states) return [];
  return [{ id: obj.id, updates: { editor: { ...obj.editor, preview_state: on ? states.on : states.off } } }];
}
