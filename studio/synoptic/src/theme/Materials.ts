// feat/room-plan: materials for floors and walls.
//
// Every texture here is GENERATED, never loaded: one small tileable
// canvas per material, drawn once and cached. No image files enter the
// repo, nothing is fetched at runtime (the editor is served from a
// loopback dist/ with no asset pipeline for binaries), and a texture
// costs a few hundred bytes of code instead of a committed PNG.
//
// Randomness is SEEDED. A texture redrawn with Math.random would
// re-scatter its grain on every React re-render, so an OSB floor would
// visibly crawl while you drag a wall across it. The tiny PRNG below
// makes each material's pattern identical every time it is built.
//
// Style target: early-2000s low-poly game - flat, untextured-looking
// shading on the wall BODIES (three tones, no gradients) with a
// readable material pattern on the large flat surfaces. Detail lives
// where there is room for it, not on every polygon edge.

const TILE = 64;

/** Deterministic PRNG (mulberry32). Same seed, same texture, every build - see this file's header for why that matters. */
function makeRandom(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), 1 | t);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export type FloorMaterialId = 'osb' | 'parkiet' | 'wykladzina' | 'beton';
export type WallMaterialId = 'tynk' | 'beton' | 'cegla' | 'osb';

export interface MaterialDef {
  id: string;
  label: string;
  /** Flat fallback color - used for the wall body tones and any place a pattern is not appropriate. Also what a material looks like before its tile is built. */
  base: string;
  draw: (ctx: CanvasRenderingContext2D) => void;
}

// ---- Floor materials ----------------------------------------------------

export const FLOOR_MATERIALS: Record<FloorMaterialId, MaterialDef> = {
  osb: {
    id: 'osb',
    label: 'OSB board',
    base: '#C9A063',
    draw: (ctx) => {
      const rnd = makeRandom(1337);
      ctx.fillStyle = '#C9A063';
      ctx.fillRect(0, 0, TILE, TILE);
      // OSB reads as flat strands of chip lying at random angles. 70
      // of them at this tile size is dense enough to read as a board
      // and sparse enough that the base color still shows between.
      for (let i = 0; i < 70; i++) {
        const x = rnd() * TILE;
        const y = rnd() * TILE;
        const w = 6 + rnd() * 16;
        const h = 3 + rnd() * 5;
        const angle = rnd() * Math.PI;
        const shade = rnd();
        ctx.save();
        ctx.translate(x, y);
        ctx.rotate(angle);
        ctx.fillStyle = shade > 0.55 ? '#D9B57E' : shade > 0.25 ? '#B88A4D' : '#A87A3E';
        ctx.globalAlpha = 0.75;
        ctx.fillRect(-w / 2, -h / 2, w, h);
        ctx.restore();
      }
    },
  },
  parkiet: {
    id: 'parkiet',
    label: 'Parquet',
    base: '#A9702F',
    draw: (ctx) => {
      const rnd = makeRandom(4242);
      const plankH = TILE / 4;
      for (let row = 0; row < 4; row++) {
        // Alternate the tone per plank and offset every other row, so
        // the tile reads as laid boards rather than as stripes.
        const tones = ['#B77B36', '#A9702F', '#9C6529', '#C08842'];
        const offset = (row % 2) * (TILE / 2);
        for (let seg = -1; seg < 2; seg++) {
          const x = offset + seg * TILE;
          ctx.fillStyle = tones[Math.floor(rnd() * tones.length)];
          ctx.fillRect(x, row * plankH, TILE, plankH);
          // Board ends and the groove between rows.
          ctx.strokeStyle = 'rgba(60,35,10,0.55)';
          ctx.lineWidth = 1;
          ctx.strokeRect(x + 0.5, row * plankH + 0.5, TILE - 1, plankH - 1);
        }
        // A couple of grain lines per row - enough to read as wood at
        // canvas zoom, cheap enough to redraw freely.
        ctx.strokeStyle = 'rgba(70,40,12,0.25)';
        for (let g = 0; g < 3; g++) {
          const gy = row * plankH + 2 + rnd() * (plankH - 4);
          ctx.beginPath();
          ctx.moveTo(0, gy);
          ctx.lineTo(TILE, gy);
          ctx.stroke();
        }
      }
    },
  },
  wykladzina: {
    id: 'wykladzina',
    label: 'Technical carpet (grey)',
    base: '#8C8C8C',
    draw: (ctx) => {
      const rnd = makeRandom(909);
      ctx.fillStyle = '#8C8C8C';
      ctx.fillRect(0, 0, TILE, TILE);
      // Fine two-tone speckle - the flecked look of a contract carpet
      // tile. Single pixels, deliberately: anything larger stops
      // reading as pile and starts reading as dirt.
      for (let i = 0; i < 900; i++) {
        ctx.fillStyle = rnd() > 0.5 ? 'rgba(255,255,255,0.16)' : 'rgba(0,0,0,0.16)';
        ctx.fillRect(rnd() * TILE, rnd() * TILE, 1, 1);
      }
    },
  },
  beton: {
    id: 'beton',
    label: 'Concrete',
    base: '#ABABAB',
    draw: (ctx) => {
      const rnd = makeRandom(77);
      ctx.fillStyle = '#ABABAB';
      ctx.fillRect(0, 0, TILE, TILE);
      // Soft mottling rather than speckle: big, very faint blotches.
      for (let i = 0; i < 40; i++) {
        const r = 3 + rnd() * 10;
        ctx.beginPath();
        ctx.arc(rnd() * TILE, rnd() * TILE, r, 0, Math.PI * 2);
        ctx.fillStyle = rnd() > 0.5 ? 'rgba(255,255,255,0.10)' : 'rgba(0,0,0,0.08)';
        ctx.fill();
      }
    },
  },
};

// ---- Wall materials ------------------------------------------------------

export const WALL_MATERIALS: Record<WallMaterialId, MaterialDef> = {
  tynk: {
    id: 'tynk',
    label: 'White plaster',
    base: '#EDEDED',
    draw: (ctx) => {
      ctx.fillStyle = '#EDEDED';
      ctx.fillRect(0, 0, TILE, TILE);
    },
  },
  beton: FLOOR_MATERIALS.beton,
  cegla: {
    id: 'cegla',
    label: 'Brick',
    base: '#9E5540',
    draw: (ctx) => {
      const rnd = makeRandom(2024);
      const courseH = TILE / 4;
      const brickW = TILE / 2;
      ctx.fillStyle = '#C9C3B8'; // mortar
      ctx.fillRect(0, 0, TILE, TILE);
      for (let row = 0; row < 4; row++) {
        const offset = (row % 2) * (brickW / 2);
        for (let col = -1; col < 3; col++) {
          const x = offset + col * brickW;
          const tones = ['#9E5540', '#8E4A37', '#AA5F48', '#96503C'];
          ctx.fillStyle = tones[Math.floor(rnd() * tones.length)];
          ctx.fillRect(x + 1, row * courseH + 1, brickW - 2, courseH - 2);
        }
      }
    },
  },
  osb: FLOOR_MATERIALS.osb,
};

// ---- Tile cache ----------------------------------------------------------

const tileCache = new Map<string, HTMLCanvasElement>();

/**
 * The tileable canvas for one material, built on first use and cached
 * forever after. Konva accepts a canvas element directly as a
 * fillPatternImage source, so no data-URL round trip is needed.
 *
 * Returns null when there is no DOM to draw on (the vitest/jsdom
 * environment some tests run in, or any future server-side render) -
 * every caller falls back to the material's flat `base` color, so a
 * missing pattern degrades to a solid fill instead of throwing.
 */
export function getMaterialTile(material: MaterialDef): HTMLCanvasElement | null {
  const cached = tileCache.get(material.id);
  if (cached) return cached;
  if (typeof document === 'undefined') return null;

  const canvas = document.createElement('canvas');
  canvas.width = TILE;
  canvas.height = TILE;
  const ctx = canvas.getContext('2d');
  if (!ctx) return null;
  material.draw(ctx);
  tileCache.set(material.id, canvas);
  return canvas;
}

export const DEFAULT_FLOOR_MATERIAL: FloorMaterialId = 'wykladzina';
export const DEFAULT_WALL_MATERIAL: WallMaterialId = 'tynk';

/** The floor material for an id, falling back to the default for an absent or unknown one - a project file naming a material this build does not have must still open. */
export function getFloorMaterial(id: FloorMaterialId | undefined): MaterialDef {
  return FLOOR_MATERIALS[id as FloorMaterialId] ?? FLOOR_MATERIALS[DEFAULT_FLOOR_MATERIAL];
}

/** Same contract as getFloorMaterial, for walls. */
export function getWallMaterial(id: WallMaterialId | undefined): MaterialDef {
  return WALL_MATERIALS[id as WallMaterialId] ?? WALL_MATERIALS[DEFAULT_WALL_MATERIAL];
}

/**
 * The three flat tones one wall material is shaded with: its top
 * surface (lit), the face turned toward the viewer (mid), and the
 * floor footprint (dark). Derived from the material's own base color
 * by a fixed lighten/darken, so every material shades consistently and
 * a new one needs no hand-picked palette.
 */
export function wallFaceTones(material: MaterialDef): { top: string; side: string; base: string } {
  return {
    top: shade(material.base, 1.06),
    side: shade(material.base, 0.78),
    base: shade(material.base, 0.5),
  };
}

/** Multiplies an #rrggbb color's channels by `factor`, clamped. Pure, no DOM - safe in any environment. */
export function shade(hex: string, factor: number): string {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex.trim());
  if (!m) return hex;
  const value = parseInt(m[1], 16);
  const clamp = (n: number) => Math.max(0, Math.min(255, Math.round(n)));
  const r = clamp(((value >> 16) & 0xff) * factor);
  const g = clamp(((value >> 8) & 0xff) * factor);
  const b = clamp((value & 0xff) * factor);
  return `#${((r << 16) | (g << 8) | b).toString(16).padStart(6, '0')}`;
}
