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
export type WorkspaceLayout = 'single' | 'rows' | 'columns' | 'grid' | 'cascade';

/** Menu/label text for each arrangement, in one place so the menu and the tab bar cannot drift apart. */
export const WORKSPACE_LAYOUTS: { id: WorkspaceLayout; label: string; hint: string }[] = [
  { id: 'single', label: 'Single', hint: 'Only the active screen' },
  { id: 'rows', label: 'Stacked', hint: 'Screens one under another' },
  { id: 'columns', label: 'Side by side', hint: 'Screens next to each other' },
  { id: 'grid', label: 'Tiled', hint: 'Screens laid out in a grid' },
  { id: 'cascade', label: 'Cascade', hint: 'Screens stacked on top of each other, offset' },
];

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
