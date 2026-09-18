// feat/workspace: how several synoptic screens share the drawing area.
//
// The grey space under the canvas was doing nothing. A controller runs
// more than one room, and an operator watching a hall while wiring the
// office next door needs both on screen - so the drawing area becomes a
// WORKSPACE holding several screens at once, arranged the way every
// drawing application has arranged its documents since MDI: stacked,
// side by side, tiled, or cascaded.
//
// Pure geometry, no React and no store - the same contract every other
// module in this folder keeps. The component asks for rectangles and
// draws in them; this file decides where they go, and a test can check
// the arithmetic without mounting anything.

/** The arrangements offered. `single` is the one-screen view the editor had before, kept as a first-class choice rather than as "a grid with one cell". */
export type WorkspaceLayout = 'single' | 'rows' | 'columns' | 'grid' | 'cascade' | 'free';

/** Menu/label text for each arrangement, in one place so the menu and the tab bar cannot drift apart. */
export const WORKSPACE_LAYOUTS: { id: WorkspaceLayout; label: string; hint: string }[] = [
  { id: 'single', label: 'Single', hint: 'Only the active screen' },
  { id: 'rows', label: 'Stacked', hint: 'Screens one under another' },
  { id: 'columns', label: 'Side by side', hint: 'Screens next to each other' },
  { id: 'grid', label: 'Tiled', hint: 'Screens laid out in a grid' },
  { id: 'cascade', label: 'Cascade', hint: 'Screens stacked on top of each other, offset' },
  { id: 'free', label: 'Free', hint: 'Windows where you drop them - drag a caption; drop at an edge to snap to half or full' },
];

// feat/window-snapping (user, 2026-09-18: "łapiesz za górę, przeciągasz,
// do góry / do boku równiutko wchodzi na pół ekranu - ustawianie rodem z
// Windowsa"): a tile dragged by its caption goes where it is dropped, and
// a drop at an edge snaps it exactly as Windows does - the top edge
// fills the area, a side edge takes that half, a corner takes that
// quarter. Once a tile has been dragged the arrangement is `free` and
// every tile keeps a FRAME: its place as fractions of the area, so the
// windows keep their proportions when the workspace itself is resized.

/** A tile's place as fractions (0..1) of the workspace area. */
export interface TileFrame {
  x: number;
  y: number;
  width: number;
  height: number;
}

/** How close to an edge (in pixels) the pointer has to be dropped for the tile to snap there. */
export const SNAP_MARGIN = 28;

export const FULL_FRAME: TileFrame = { x: 0, y: 0, width: 1, height: 1 };

/**
 * The frame a drop at pointer (px, py) snaps to, or null away from every
 * edge. Corners win over edges (a pointer in the top-left corner is also
 * at the top edge, and the quarter is the more specific answer); the
 * bottom edge alone snaps to nothing, the same as Windows.
 */
export function snapZone(px: number, py: number, width: number, height: number): TileFrame | null {
  if (width <= 0 || height <= 0) return null;
  const left = px <= SNAP_MARGIN;
  const right = px >= width - SNAP_MARGIN;
  const top = py <= SNAP_MARGIN;
  const bottom = py >= height - SNAP_MARGIN;
  if (top && left) return { x: 0, y: 0, width: 0.5, height: 0.5 };
  if (top && right) return { x: 0.5, y: 0, width: 0.5, height: 0.5 };
  if (bottom && left) return { x: 0, y: 0.5, width: 0.5, height: 0.5 };
  if (bottom && right) return { x: 0.5, y: 0.5, width: 0.5, height: 0.5 };
  if (top) return FULL_FRAME;
  if (left) return { x: 0, y: 0, width: 0.5, height: 1 };
  if (right) return { x: 0.5, y: 0, width: 0.5, height: 1 };
  return null;
}

export function isFullFrame(frame: TileFrame | undefined): boolean {
  return !!frame && frame.x === 0 && frame.y === 0 && frame.width === 1 && frame.height === 1;
}

/** A pixel rectangle as a frame of the `width` x `height` area, kept inside it and never smaller than MIN_TILE. */
export function frameFromRect(rect: { x: number; y: number; width: number; height: number }, width: number, height: number): TileFrame {
  if (width <= 0 || height <= 0) return FULL_FRAME;
  const w = Math.min(width, Math.max(MIN_TILE, rect.width));
  const h = Math.min(height, Math.max(MIN_TILE, rect.height));
  const x = Math.min(Math.max(0, rect.x), width - w);
  const y = Math.min(Math.max(0, rect.y), height - h);
  return { x: x / width, y: y / height, width: w / width, height: h / height };
}

/** A frame back in pixels for the current area. */
export function rectFromFrame(frame: TileFrame, width: number, height: number): { x: number; y: number; width: number; height: number } {
  return {
    x: Math.round(frame.x * width),
    y: Math.round(frame.y * height),
    width: Math.max(1, Math.round(frame.width * width)),
    height: Math.max(1, Math.round(frame.height * height)),
  };
}

/**
 * Tiles for the free arrangement: a screen with a frame sits where its
 * frame says, one without (a screen added after the arrangement was
 * freed) takes the place the fallback arrangement would give it. `z`
 * follows the order given, the active tile is raised by the component.
 */
export function freeTileRects(
  screenIds: string[],
  frames: Record<string, TileFrame>,
  fallback: WorkspaceTile[],
  width: number,
  height: number
): WorkspaceTile[] {
  return screenIds.map((id, index) => {
    const frame = frames[id];
    if (!frame) return fallback[index] ?? { x: 0, y: 0, width, height, z: index };
    return { ...rectFromFrame(frame, width, height), z: index };
  });
}

/**
 * The screens actually on show, in PROJECT order.
 *
 * Project order, not "active first": tiles must stay where they are when
 * a different one becomes active. A workspace whose windows swapped
 * places every time you clicked one would be impossible to work in.
 *
 * The active screen is always among them - an active screen you cannot
 * see is not a state worth being able to reach - and a deleted screen is
 * never produced, because the list is built from the screens that exist.
 */
export function visibleScreens(
  hidden: string[],
  activeScreenId: string,
  layout: WorkspaceLayout,
  allScreenIds: string[]
): string[] {
  if (layout === 'single') return [activeScreenId];
  const hiddenSet = new Set(hidden);
  return allScreenIds.filter(id => id === activeScreenId || !hiddenSet.has(id));
}

/** One screen's place in the workspace. `z` orders overlapping panes - it only ever differs from the array index in `cascade`, where panes genuinely overlap. */
export interface WorkspaceTile {
  x: number;
  y: number;
  width: number;
  height: number;
  z: number;
}

/** The gutter between tiles. Small: this is a drawing area, and every pixel spent on chrome is a pixel not spent on the room. */
export const TILE_GAP = 4;

/** A tile narrower or shorter than this is not a view of anything - below roughly this size a room fits in too few pixels to read. Used to cap how many panes an arrangement will lay out in the space available. */
export const MIN_TILE = 120;

/** How far each cascaded pane is offset from the one below it. A full title bar's worth, so the pane underneath still shows enough to be clicked. */
const CASCADE_STEP = 26;

/** Cascaded panes are this fraction of the area, leaving room for the offsets. */
const CASCADE_FILL = 0.72;

/**
 * Where each of `count` panes goes, in an area `width` x `height`.
 *
 * Always returns exactly `count` tiles, even when the area is too small
 * for them to be useful: clamping the COUNT here would mean a screen the
 * user explicitly added silently not existing, which is worse than a
 * cramped one. fitsComfortably() below is how a caller asks the other
 * question.
 */
export function tileRects(
  layout: WorkspaceLayout,
  count: number,
  width: number,
  height: number
): WorkspaceTile[] {
  if (count <= 0) return [];
  if (count === 1 || layout === 'single') {
    return [{ x: 0, y: 0, width, height, z: 0 }];
  }
  // `free` has no arithmetic of its own here: a screen without a frame
  // yet (freeTileRects) takes the grid's place, so the grid is what this
  // function answers with for it.
  if (layout === 'free') layout = 'grid';

  if (layout === 'cascade') {
    const paneWidth = Math.max(MIN_TILE, width * CASCADE_FILL);
    const paneHeight = Math.max(MIN_TILE, height * CASCADE_FILL);
    // The offsets must not walk the last pane off the edge, so the step
    // shrinks once there are more panes than there is room to step.
    const spanX = Math.max(0, width - paneWidth);
    const spanY = Math.max(0, height - paneHeight);
    const step = Math.min(CASCADE_STEP, count > 1 ? Math.min(spanX, spanY) / (count - 1) : CASCADE_STEP);
    return Array.from({ length: count }, (_, i) => ({
      x: Math.round(i * step),
      y: Math.round(i * step),
      width: Math.round(paneWidth),
      height: Math.round(paneHeight),
      z: i,
    }));
  }

  const { columns, rows } = gridShape(layout, count);
  const cellWidth = (width - TILE_GAP * (columns - 1)) / columns;
  const cellHeight = (height - TILE_GAP * (rows - 1)) / rows;

  return Array.from({ length: count }, (_, i) => {
    const column = i % columns;
    const row = Math.floor(i / columns);
    // The last row of a grid is often short (5 panes in a 3x2). Those
    // panes stretch to fill their row rather than leaving a gap at the
    // end, which is what every tiling window manager does and what looks
    // deliberate rather than broken.
    const inLastRow = row === rows - 1;
    const lastRowCount = count - columns * (rows - 1);
    const span = inLastRow && lastRowCount > 0 ? lastRowCount : columns;
    const stretchedWidth = span === columns
      ? cellWidth
      : (width - TILE_GAP * (span - 1)) / span;
    const stretchedColumn = span === columns ? column : i - columns * (rows - 1);

    return {
      x: Math.round(stretchedColumn * (stretchedWidth + TILE_GAP)),
      y: Math.round(row * (cellHeight + TILE_GAP)),
      width: Math.round(Math.max(1, stretchedWidth)),
      height: Math.round(Math.max(1, cellHeight)),
      z: i,
    };
  });
}

/** How many columns and rows an arrangement uses for `count` panes. */
export function gridShape(layout: WorkspaceLayout, count: number): { columns: number; rows: number } {
  switch (layout) {
    // "Jeden pod drugim" - full-width bands, one per screen.
    case 'rows':
      return { columns: 1, rows: count };
    // "Obok siebie" - full-height columns.
    case 'columns':
      return { columns: count, rows: 1 };
    case 'grid': {
      // As square as possible, wider than tall when it cannot be square:
      // a screen is a room seen from above, and rooms are usually wider
      // than they are deep.
      const columns = Math.ceil(Math.sqrt(count));
      return { columns, rows: Math.ceil(count / columns) };
    }
    default:
      return { columns: 1, rows: 1 };
  }
}

/** Whether `count` panes still read as views rather than as stamps, in the space available. The tab bar uses this to warn before an arrangement becomes useless, without preventing it. */
export function fitsComfortably(
  layout: WorkspaceLayout,
  count: number,
  width: number,
  height: number
): boolean {
  if (count <= 1) return true;
  return tileRects(layout, count, width, height)
    .every(tile => tile.width >= MIN_TILE && tile.height >= MIN_TILE);
}
