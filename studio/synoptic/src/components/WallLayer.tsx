// Konva rendering for walls (feat/room-plan).
//
// Walls are painted as BODIES, not as elements. WallGeometry.ts groups
// connected walls into chains and offsets each chain into one mitred
// ring, so a room is filled and outlined ONCE - no overlapping
// rectangles, no doubled outlines, no notches where two walls meet.
// That is the whole reason this is a layer component rather than the
// per-wall node it replaced: a wall's corner cannot be drawn without
// knowing its neighbour.
//
// Interaction stays PER WALL. Selection and dragging still address one
// wall at a time, through invisible hit shapes over the painted body -
// the geometry belongs to the chain, the editable object is still the
// individual wall.
//
// ---------------------------------------------------------------------
// HOW THE CUT-AWAY VIEW IS BUILT, and what each piece is for.
//
// The projection lifts "up" straight up the screen and never moves a
// footprint, so plan coordinates stay plan coordinates (see
// WallElement.drawnWallHeight). Everything below is paint.
//
//   1. TOP SURFACE - the wall ring at its footprint, carrying the
//      material. This is the plan: a wall seen from above. It is NOT
//      lifted. Lifting the whole ring was the first attempt and it put
//      a full band of wall material straight across the middle of the
//      room, because lifting everything moves the NEAR wall's top
//      surface into the room it encloses.
//   2. FAR FACES - the inside face of the wall furthest from the
//      viewer, rising to full height. This is the surface a cut-away
//      view exists to show.
//   3. CAPS - a strip the thickness of the wall along the top of each
//      far face, so the wall has a visible top rather than ending in a
//      bare edge. Drawn per face, which is what lets the far wall have
//      a cap while the near one does not.
//   4. NEAR FACES - cut down to a stub, so the near wall never stands
//      between the viewer and the room, exactly as an architectural
//      section does.
//   5. ARRIS + SKIRTING - the highlight where cap meets face, and the
//      line where wall meets floor. Two hairlines, and most of what
//      makes the result read as built rather than diagrammed.

import React from 'react';
import { Circle, Group, Line } from 'react-konva';
import type { WallElement } from '../elements/WallElement';
import { clampWallThickness, computeWallFaces } from '../elements/WallElement';
import {
  bandsFromWalls, extrudeBand, openEndPoints, ringToPoints,
} from '../project/WallGeometry';
import type { WallBand, WallFace } from '../project/WallGeometry';
import { findWallOpenings, openingCutPolygon, openingJambs } from '../project/WallOpenings';
import type { WallOpening } from '../project/WallOpenings';
import type { SynopticObject } from '../store';
import { getMaterialTile, getWallMaterial, shade, wallFaceTones } from '../theme/Materials';
import type { WallMaterialId } from '../theme/Materials';
import { COLOR_OUTLINE } from '../theme/ScadaTheme';

const EDGE_WIDTH = 1.25;

// CUT-AWAY. How much of the near wall's height survives.
//
// 0.16 was too little: the near wall came out as a hairline, so the
// bottom of a room read as an open edge and anything seated in that
// wall - a door, a gate - looked like it was floating beside the room
// rather than set into it. This is enough wall to be a wall, and still
// far too little to stand between the viewer and the room.
const NEAR_WALL_CUTAWAY = 0.3;

// FLAT SHADING. One fixed light from the upper left, one dot product
// per face, no gradients and no smoothing - the whole low-poly look.
// Only the x component of a face's normal varies among the faces this
// projection draws, so that is all the light needs.
const LIGHT_X = -0.75;
const SHADE_RANGE = 0.22;

// A vertical face is darker than a horizontal one no matter which way
// it points - that is what separates a wall's side from its top at a
// glance, before any directional light is applied. The light then
// modulates around this base.
//
// This has to be applied to the SHADE FACTOR rather than by picking a
// darker colour, because a textured face is painted with the material's
// own tile and Konva cannot tint a pattern. Passing the darker tone and
// then not using it (which the first version of ShadedFace did
// whenever a tile existed) left every face rendering at full material
// brightness - the wall's face and its top came out the same colour and
// the whole body flattened.
const FACE_BASE_SHADE = 0.78;
const CAP_SHADE = 1.06;

/** How strongly a shade factor paints over the material. Tuned so the base side-darkening reads clearly without turning brick into mud. */
const SHADE_OVERLAY_STRENGTH = 1.1;

// The arris - the lit edge where a wall's top meets its face. A single
// hairline, and out of all the detail here the one that does most to
// stop the wall reading as a flat grey band.
const ARRIS_COLOR = '#FFFFFF';
const ARRIS_OPACITY = 0.55;

// The skirting line where wall meets floor, just inside the room.
const SKIRTING_COLOR = '#000000';
const SKIRTING_OPACITY = 0.22;

// An open end is marked with a dot. The extruded body makes it hard to
// tell where a wall stops - the painted body is lifted, so the end you
// are aiming at is not where the paint ends. The dots disappear on
// their own the moment a corner joins two walls, so a finished room has
// none and an unfinished one shows exactly the ends still to be joined.
const OPEN_END_RADIUS = 4.5;
const OPEN_END_FILL = '#FFFFFF';
const OPEN_END_STROKE = '#0064C8';

// The body's own shadow on the ground. Offset away from the light that
// shades the faces, so the two agree about where it is coming from.
const GROUND_SHADOW_BLUR = 10;
const GROUND_SHADOW_OFFSET = 5;
const GROUND_SHADOW_OPACITY = 0.18;

const SELECTION_COLOR = '#00A0FF';

function shadeForNormal(normalX: number): number {
  return 1 + normalX * LIGHT_X * SHADE_RANGE;
}

/** Shortens an extruded face to the cut-away stub - only the two top corners move. */
function cutAway(points: number[]): number[] {
  const [ax, ay, bx, by, , topB, , topA] = points;
  return [
    ax, ay, bx, by,
    bx, by - (by - topB) * NEAR_WALL_CUTAWAY,
    ax, ay - (ay - topA) * NEAR_WALL_CUTAWAY,
  ];
}

/** The wall's top, as a strip sitting on a face's upper edge. Per face rather than as one lifted ring - that is what lets the far wall be capped while the near, cut-away one is not. */
function capForFace(points: number[], thickness: number): number[] {
  const [, , bx, , , topB, ax, topA] = points;
  return [ax, topA, bx, topB, bx, topB - thickness, ax, topA - thickness];
}

/** A face's top edge, as a line - the arris. */
function arrisForFace(points: number[]): number[] {
  const [, , bx, , , topB, ax, topA] = points;
  return [ax, topA, bx, topB];
}

export interface WallLayerProps {
  walls: WallElement[];
  /** Needed only to find the openings seated in these walls - see WallOpenings.ts. */
  objects: SynopticObject[];
  selectedWallIds: string[];
  previewMode: boolean;
  onSelect: (wallId: string, e: any) => void;
  onDragEnd: (wallId: string, dx: number, dy: number) => void;
}

/**
 * One vertical face: the material, then a flat shade over it.
 *
 * Two passes rather than one tinted fill, because Konva cannot tint a
 * pattern. The pattern goes down first and a solid overlay at low alpha
 * darkens or lightens it - which keeps brick reading as brick on a
 * shaded wall instead of flattening every material to its own grey.
 */
const ShadedFace: React.FC<{
  points: number[];
  tile: HTMLCanvasElement | null;
  flatTone: string;
  shadeFactor: number;
}> = ({ points, tile, flatTone, shadeFactor }) => {
  if (!tile) {
    return <Line points={points} closed fill={shade(flatTone, shadeFactor)} listening={false} />;
  }
  // Positive factor lightens, negative darkens; the overlay colour and
  // its alpha both come from how far the factor is from neutral.
  const delta = shadeFactor - 1;
  const overlayAlpha = Math.min(0.55, Math.abs(delta) * SHADE_OVERLAY_STRENGTH);
  return (
    <>
      <Line
        points={points}
        closed
        fillPatternImage={tile as unknown as HTMLImageElement}
        fillPatternRepeat="repeat"
        listening={false}
      />
      {Math.abs(delta) > 0.001 && (
        <Line
          points={points}
          closed
          fill={delta > 0 ? '#FFFFFF' : '#000000'}
          opacity={overlayAlpha}
          listening={false}
        />
      )}
    </>
  );
};

const BandBody: React.FC<{ band: WallBand; openings: WallOpening[] }> = ({ band, openings }) => {
  const material = getWallMaterial(band.material as WallMaterialId | undefined);
  // wallFaceTones stays for the ONE place that still needs a ready-made
  // colour rather than a factor: the top surface's no-tile fallback.
  const tones = wallFaceTones(material);
  const tile = getMaterialTile(material);
  const thickness = clampWallThickness(band.thickness);

  const faces = extrudeBand(band).sort((a, b) => a.depth - b.depth);
  const farFaces = faces.filter(f => f.side === 'inner');
  const nearFaces = faces.filter(f => f.side === 'outer');

  // Openings are cut by CLIPPING rather than by boolean-subtracting
  // polygons: Konva has no path arithmetic, but its clip does honour a
  // path's winding. An outer rectangle traced clockwise with each
  // opening traced anticlockwise inside it leaves exactly the wall
  // minus its openings under the default non-zero rule - one clip for
  // the whole body, so every piece above gets the same holes without
  // any of them needing to know openings exist.
  const cuts = openings.map(openingCutPolygon);
  const clipFunc = cuts.length === 0 ? undefined : (ctx: any) => {
    ctx.beginPath();
    ctx.moveTo(-100000, -100000);
    ctx.lineTo(100000, -100000);
    ctx.lineTo(100000, 100000);
    ctx.lineTo(-100000, 100000);
    ctx.closePath();
    for (const cut of cuts) {
      const reversed = [...cut].reverse();
      ctx.moveTo(reversed[0].x, reversed[0].y);
      for (let i = 1; i < reversed.length; i++) ctx.lineTo(reversed[i].x, reversed[i].y);
      ctx.closePath();
    }
  };

  const renderFace = (face: WallFace, key: string, points: number[]) => (
    <ShadedFace
      key={key}
      points={points}
      tile={tile}
      flatTone={material.base}
      shadeFactor={FACE_BASE_SHADE * shadeForNormal(face.normalX)}
    />
  );

  return (
    <Group listening={false} clipFunc={clipFunc}>
      {/* Ground shadow. Konva's own shape shadow, on a copy of the
          footprint drawn before everything else - offset down-right,
          away from the same upper-left light the faces are shaded by.
          Without it the body reads as a sticker lying on the grid;
          with it, it stands on it.

          The room is punched out of it (evenodd), exactly like every
          other ring here. The first version filled the whole outer
          polygon instead, which laid 18% black over the entire FLOOR -
          the floor is drawn underneath this layer - and turned a
          mid-grey carpet into near-charcoal. */}
      <Line
        points={band.inner
          ? [...ringToPoints(band.outer), ...ringToPoints(band.inner)]
          : ringToPoints(band.outer)}
        closed
        fillRule="evenodd"
        fill="#000000"
        opacity={GROUND_SHADOW_OPACITY}
        shadowColor="#000000"
        shadowBlur={GROUND_SHADOW_BLUR}
        shadowOpacity={0.55}
        shadowOffsetX={GROUND_SHADOW_OFFSET}
        shadowOffsetY={GROUND_SHADOW_OFFSET}
        listening={false}
      />
      {/* 2 + 3: the far wall - its cap first, then its face, so the
          face's own outline sits on top of the join. */}
      {farFaces.map((face, i) => (
        <React.Fragment key={`far-${i}`}>
          <ShadedFace
            points={capForFace(face.points, thickness)}
            tile={tile}
            flatTone={material.base}
            // The cap faces the sky: always the lightest surface on the
            // wall, whichever way the wall itself runs.
            shadeFactor={CAP_SHADE}
          />
          {renderFace(face, `far-face-${i}`, face.points)}
          <Line
            points={capForFace(face.points, thickness)}
            closed
            stroke={COLOR_OUTLINE}
            strokeWidth={EDGE_WIDTH}
            listening={false}
          />
          {/* 5: the arris. */}
          <Line
            points={arrisForFace(face.points)}
            stroke={ARRIS_COLOR}
            strokeWidth={1.5}
            opacity={ARRIS_OPACITY}
            listening={false}
          />
        </React.Fragment>
      ))}

      {/* 1: the wall's top surface, on the plan, with the room punched
          out of it (evenodd) so it never buries the floor. */}
      <Line
        points={band.inner
          ? [...ringToPoints(band.outer), ...ringToPoints(band.inner)]
          : ringToPoints(band.outer)}
        closed
        {...(tile
          ? { fillPatternImage: tile as unknown as HTMLImageElement, fillPatternRepeat: 'repeat' }
          : { fill: tones.top })}
        fillRule="evenodd"
        listening={false}
      />

      {/* 4: the near wall, cut to a stub. */}
      {nearFaces.map((face, i) => renderFace(face, `near-${i}`, cutAway(face.points)))}

      {/* Outlines last, so nothing paints over them. One stroke per
          ring - this is the line that used to be drawn four times over
          itself at every corner. */}
      <Line points={ringToPoints(band.outer)} closed stroke={COLOR_OUTLINE} strokeWidth={EDGE_WIDTH} listening={false} />
      {band.inner && (
        <>
          <Line points={ringToPoints(band.inner)} closed stroke={COLOR_OUTLINE} strokeWidth={EDGE_WIDTH} listening={false} />
          {/* 5: skirting - a hairline just inside the room, where the
              wall meets the floor. */}
          <Line
            points={ringToPoints(band.inner)}
            closed
            stroke={SKIRTING_COLOR}
            strokeWidth={3}
            opacity={SKIRTING_OPACITY}
            listening={false}
          />
        </>
      )}
    </Group>
  );
};

export const WallLayer: React.FC<WallLayerProps> = ({
  walls, objects, selectedWallIds, previewMode, onSelect, onDragEnd,
}) => {
  if (walls.length === 0) return null;

  const bands = bandsFromWalls(walls);
  const openEnds = openEndPoints(walls);
  const openings = findWallOpenings(walls, objects);

  return (
    <Group>
      {bands.map((band, i) => (
        <BandBody
          key={`band-${i}`}
          band={band}
          // Only the openings seated in THIS body's own walls - an
          // opening in another room must not punch a hole here.
          openings={openings.filter(o => band.wallIds.includes(o.wallId))}
        />
      ))}

      {/* Jambs: the reveals closing each cut. Drawn after the bodies
          (and outside their clip, or they would be clipped away by the
          very hole they are closing) so an opening reads as a finished
          reveal rather than as a gap where the wall simply stops. */}
      {openings.flatMap(opening => openingJambs(opening).map((jamb, i) => (
        <Line
          key={`jamb-${opening.objectId}-${i}`}
          points={[jamb[0].x, jamb[0].y, jamb[1].x, jamb[1].y]}
          stroke={COLOR_OUTLINE}
          strokeWidth={EDGE_WIDTH}
          listening={false}
        />
      )))}

      {/* Selection highlight, over the body but under the hit shapes. */}
      {walls.filter(w => selectedWallIds.includes(w.id)).map(wall => (
        <Line
          key={`sel-${wall.id}`}
          points={[wall.from.x, wall.from.y, wall.to.x, wall.to.y]}
          stroke={SELECTION_COLOR}
          strokeWidth={clampWallThickness(wall.thickness) + 3}
          opacity={0.55}
          lineCap="butt"
          listening={false}
        />
      ))}

      {/* Invisible per-wall hit shapes - the editable object is still
          one wall, however the body was merged for painting.

          These cover the WHOLE PAINTED BODY, not just the footprint.
          The footprint alone was the earlier version and it made walls
          feel unclickable: the wall you see is drawn lifted, so aiming
          at the painted band landed the cursor above a hit area sitting
          at floor level. */}
      {walls.map(wall => {
        const faces = computeWallFaces(wall);
        if (faces.base.length === 0) return null;
        const hitProps = {
          draggable: !previewMode,
          onClick: (e: any) => onSelect(wall.id, e),
          onTap: (e: any) => onSelect(wall.id, e),
          onDragEnd: (e: any) => {
            const node = e.target;
            const dx = node.x();
            const dy = node.y();
            node.x(0);
            node.y(0);
            onDragEnd(wall.id, dx, dy);
          },
          // A transparent FILL still takes hits in Konva; a transparent
          // stroke would not cover the polygon's interior.
          fill: 'transparent',
          closed: true,
        };
        return (
          <Group key={`hit-${wall.id}`}>
            <Line points={faces.base} {...hitProps} />
            {faces.side.length > 0 && <Line points={faces.side} {...hitProps} />}
          </Group>
        );
      })}

      {/* Open ends - see OPEN_END_RADIUS above for why these exist. */}
      {openEnds.map((p, i) => (
        <Circle
          key={`end-${i}`}
          x={p.x}
          y={p.y}
          radius={OPEN_END_RADIUS}
          fill={OPEN_END_FILL}
          stroke={OPEN_END_STROKE}
          strokeWidth={1.5}
          listening={false}
        />
      ))}
    </Group>
  );
};
