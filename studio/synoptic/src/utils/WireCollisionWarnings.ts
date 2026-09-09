// feat/wire-routing-around-obstacles commit 1: "komunikat pojawia sie
// RAZ na kolizje, nie przy kazdym przerysowaniu" - a collision is
// recomputed from scratch on every saveHistory() call (WireCollision.ts
// is pure, it has no memory of its own), so something else has to
// remember which (wire, obstacle) pairs already got their one Messages
// notice. A plain module-level Set, not store state - the same
// session-only-memory convention CanvasInputState.ts already
// established (see its own header) for exactly this kind of thing: it
// must never be serialized into the project file, and it must survive
// across renders without itself being a reason to re-render anything.

import type { WireCollision } from '../project/WireCollision';

let warnedKeys = new Set<string>();

function keyOf(c: WireCollision): string {
  return `${c.connectionId}:${c.obstacle.id}:${c.segmentIndex}`;
}

/**
 * Given every collision present RIGHT NOW, returns only the ones not
 * already warned about - and remembers them, so a second call with the
 * exact same collisions returns nothing. A collision that disappears
 * (fixed, or the wire/obstacle moved apart) and later reappears is
 * treated as a fresh occurrence - warned about again, per this task's
 * own wording ("RAZ na kolizje", once per collision, not once ever).
 */
export function getNewCollisionWarnings(collisions: WireCollision[]): WireCollision[] {
  const stillPresent = new Set(collisions.map(keyOf));
  // Forget anything that is no longer colliding, so it warns again if
  // it comes back later instead of staying silently "already warned"
  // forever.
  warnedKeys.forEach(key => { if (!stillPresent.has(key)) warnedKeys.delete(key); });

  const fresh: WireCollision[] = [];
  collisions.forEach(c => {
    const key = keyOf(c);
    if (warnedKeys.has(key)) return;
    warnedKeys.add(key);
    fresh.push(c);
  });
  return fresh;
}

/** Test-only reset, so one test's warnings never leak into the next. */
export function resetCollisionWarnings(): void {
  warnedKeys = new Set<string>();
}
