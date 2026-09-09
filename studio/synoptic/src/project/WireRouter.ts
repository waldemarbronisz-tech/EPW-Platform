// feat/wire-routing-around-obstacles commit 2: computing an orthogonal
// route between two points that goes AROUND a set of obstacle
// rectangles instead of through them.
//
// METHOD CHOSEN, AND WHY (raport.md repeats this - kept here too, since
// this is exactly the file it is about): a bounded Dijkstra search over
// grid nodes - the textbook "maze routing" approach for orthogonal
// point-to-point routing around rectangular keep-outs on a fixed grid.
// Each search STATE is (node, direction just arrived from), not just a
// node, so a direction change can be counted and penalized separately
// from plain distance travelled - this is what lets the search satisfy
// requirement (b) "fewest bends first" before (c) "then shortest": the
// combined cost key `turns * TURN_PENALTY + steps` makes any extra bend
// strictly worse than any amount of extra straight-line distance the
// search could ever find within its own bounded region, as long as
// TURN_PENALTY exceeds the largest possible step count in that region -
// true by construction (TURN_PENALTY is derived FROM the region's own
// node count, below). This is not the only possible method - an A*
// search with a Manhattan-distance heuristic would explore fewer nodes
// for the same result - but a plain bounded Dijkstra was chosen because
// it is straightforward to get correct and easy to reason about, and
// this task's own spec explicitly does not ask for an optimal-search
// algorithm ("nie musisz szukac trasy optymalnej... zastosowanie
// prostego przeszukiwania po siatce jest w porzadku").
//
// COMPUTATION LIMIT: WIRE_ROUTER_STEP_LIMIT (ScadaTheme, 4000) bounds
// how many grid nodes this search will ever POP off its own queue.
// Exceeding it aborts the search and falls back to the direct route
// (see directRoute below) - drawing must never hang on a complicated
// screen, per this task's own explicit requirement. 4000 was chosen as
// comfortably more than a search restricted to this file's own PADDING
// (see below) will ever need for the mandated tests (a 30-obstacle
// screen, test 16) while still cutting off quickly on a pathological
// one - not derived from a formula, a practical ceiling.

import type { WirePoint } from '../store';
import type { Obstacle } from './WireCollision';
import { segmentHitsObstacle } from './WireCollision';
import { simplifyCollinearPoints, snapPointToGrid } from '../utils/WireDrawing';
import { WIRE_ROUTER_STEP_LIMIT } from '../theme/ScadaTheme';

type DirChar = 'S' | 'U' | 'D' | 'L' | 'R';

const DIRS: { dx: number; dy: number; char: DirChar }[] = [
  { dx: 0, dy: -1, char: 'U' },
  { dx: 0, dy: 1, char: 'D' },
  { dx: -1, dy: 0, char: 'L' },
  { dx: 1, dy: 0, char: 'R' }
];

/** The direct point-to-point route, still orthogonal (one elbow if the two points share neither x nor y) - used both as the router's own fallback and as its trivial no-obstacle answer. */
function directRoute(start: WirePoint, end: WirePoint): WirePoint[] {
  if (start.x === end.x || start.y === end.y) return [{ x: start.x, y: start.y }, { x: end.x, y: end.y }];
  return [{ x: start.x, y: start.y }, { x: end.x, y: start.y }, { x: end.x, y: end.y }];
}

/** Whether the single grid step from a to b crosses any obstacle. */
function stepBlocked(a: WirePoint, b: WirePoint, obstacles: Obstacle[]): boolean {
  return obstacles.some(o => segmentHitsObstacle(a, b, o));
}

interface Frontier {
  cost: number;
  x: number;
  y: number;
  dir: DirChar;
  steps: number;
  turns: number;
}

/** A plain binary min-heap - the only data structure this router needs beyond arrays/maps, kept local rather than pulling in a library (GRANICE: no new dependency). */
class MinHeap {
  private items: Frontier[] = [];
  get size(): number { return this.items.length; }
  push(item: Frontier): void {
    this.items.push(item);
    let i = this.items.length - 1;
    while (i > 0) {
      const parent = (i - 1) >> 1;
      if (this.items[parent].cost <= this.items[i].cost) break;
      [this.items[parent], this.items[i]] = [this.items[i], this.items[parent]];
      i = parent;
    }
  }
  pop(): Frontier | undefined {
    const top = this.items[0];
    const last = this.items.pop();
    if (this.items.length > 0 && last) {
      this.items[0] = last;
      let i = 0;
      const n = this.items.length;
      while (true) {
        const l = i * 2 + 1;
        const r = i * 2 + 2;
        let smallest = i;
        if (l < n && this.items[l].cost < this.items[smallest].cost) smallest = l;
        if (r < n && this.items[r].cost < this.items[smallest].cost) smallest = r;
        if (smallest === i) break;
        [this.items[smallest], this.items[i]] = [this.items[i], this.items[smallest]];
        i = smallest;
      }
    }
    return top;
  }
}

/**
 * An orthogonal route from `start` to `end`, grid-aligned throughout,
 * that avoids every rectangle in `obstacles` - requirements (a)-(d) of
 * this commit's own spec, in that priority order. Never throws and
 * never returns an empty list: when no avoiding route can be found
 * within this search's own bounds (the goal is walled in, or the
 * WIRE_ROUTER_STEP_LIMIT above is reached first), the direct point-to-
 * point route is returned instead - still perfectly valid data (grid-
 * aligned, orthogonal), simply one this task's own commit 1 mechanism
 * will go on to flag as colliding, exactly as this task's own spec
 * requires ("zglos to jako kolizje przez mechanizm z commitu 1").
 */
export function routeAround(start: WirePoint, end: WirePoint, obstacles: Obstacle[], gridSize: number): WirePoint[] {
  const s = snapPointToGrid(start.x, start.y);
  const e = snapPointToGrid(end.x, end.y);

  if (s.x === e.x && s.y === e.y) return [s];
  if (obstacles.length === 0) return directRoute(s, e);

  // The search is restricted to a padded bounding box around the two
  // endpoints - generous enough for every obstacle this task's own
  // mandated tests place in the way, without letting a huge, mostly
  // irrelevant screen blow up the node count. PADDING is expressed in
  // grid cells so it scales sensibly with gridSize.
  const PADDING = gridSize * 8;
  const minX = Math.min(s.x, e.x) - PADDING;
  const maxX = Math.max(s.x, e.x) + PADDING;
  const minY = Math.min(s.y, e.y) - PADDING;
  const maxY = Math.max(s.y, e.y) + PADDING;

  const widthNodes = Math.round((maxX - minX) / gridSize) + 1;
  const heightNodes = Math.round((maxY - minY) / gridSize) + 1;
  // Exceeds the largest possible number of steps a loop-free path
  // through this region could ever take - see this file's own header
  // for why that is what makes the cost key's lexicographic ordering
  // (bends, then length) actually hold.
  const TURN_PENALTY = widthNodes * heightNodes + 10;

  const inBounds = (x: number, y: number) => x >= minX && x <= maxX && y >= minY && y <= maxY;

  const stateKey = (x: number, y: number, dir: DirChar) => `${x},${y},${dir}`;
  const bestCost = new Map<string, number>();
  const cameFrom = new Map<string, { x: number; y: number; dir: DirChar } | null>();

  const heap = new MinHeap();
  const startState: Frontier = { cost: 0, x: s.x, y: s.y, dir: 'S', steps: 0, turns: 0 };
  heap.push(startState);
  bestCost.set(stateKey(s.x, s.y, 'S'), 0);
  cameFrom.set(stateKey(s.x, s.y, 'S'), null);

  let goalKey: string | null = null;
  let expansions = 0;

  while (heap.size > 0) {
    const current = heap.pop()!;
    const key = stateKey(current.x, current.y, current.dir);
    if (bestCost.get(key) !== current.cost) continue; // stale entry, a cheaper one already won

    if (current.x === e.x && current.y === e.y) {
      goalKey = key;
      break;
    }

    expansions++;
    if (expansions > WIRE_ROUTER_STEP_LIMIT) break; // computation cap - fall back to the direct route below

    for (const { dx, dy, char } of DIRS) {
      const nx = current.x + dx * gridSize;
      const ny = current.y + dy * gridSize;
      if (!inBounds(nx, ny)) continue;
      if (stepBlocked({ x: current.x, y: current.y }, { x: nx, y: ny }, obstacles)) continue;

      const turned = current.dir !== 'S' && current.dir !== char;
      const nextTurns = current.turns + (turned ? 1 : 0);
      const nextSteps = current.steps + 1;
      const nextCost = nextTurns * TURN_PENALTY + nextSteps;
      const nextKey = stateKey(nx, ny, char);

      if (bestCost.has(nextKey) && bestCost.get(nextKey)! <= nextCost) continue;
      bestCost.set(nextKey, nextCost);
      cameFrom.set(nextKey, { x: current.x, y: current.y, dir: current.dir });
      heap.push({ cost: nextCost, x: nx, y: ny, dir: char, steps: nextSteps, turns: nextTurns });
    }
  }

  if (!goalKey) return directRoute(s, e); // walled in, or the step limit was reached first

  // Walk cameFrom back to the start, collecting every grid node visited.
  const dense: WirePoint[] = [];
  let cursorKey: string = goalKey;
  let cursor: { x: number; y: number; dir: DirChar } | null = { x: e.x, y: e.y, dir: goalKey.split(',')[2] as DirChar };
  while (cursor) {
    dense.push({ x: cursor.x, y: cursor.y });
    const prev = cameFrom.get(cursorKey);
    if (!prev) break;
    cursorKey = stateKey(prev.x, prev.y, prev.dir);
    cursor = prev;
  }
  dense.reverse();

  // Collapse every straight run down to its own two corner points -
  // routeAround's own contract is the polyline's VERTICES (bends plus
  // the two endpoints), not one point per grid cell stepped through.
  return simplifyCollinearPoints(dense);
}
