// feat/site-objects-2d commit 1: shared drawing primitives for the
// TEREN (site object) symbol library - a retro-industrial "banded
// shading" look, extended from (not replacing) the flat SCADA style
// every schematic symbol already uses (see ScadaTheme.ts's own header
// and its own "Site objects" section for the full palette this file
// draws from). Every proportion, band/outline thickness and arc ratio
// below is taken from docs/EPW_rysunki_referencja.py's own rect/vrect/
// circ/glow methods, translated 1:1 from its SVG output into Konva -
// that file is a geometry/color REFERENCE only (Python, never run,
// never imported), this is the real, permanent implementation.
//
// Plain functions, not components used as JSX tags: their own names
// (bandedRect, bandedVRect, bandedCircle, glow) are lowercase, so React
// would treat a <bandedRect/> tag as an unknown HTML element rather
// than a component reference - each is called directly and its result
// embedded with {...}, the same way the reference's own c.rect(...)
// calls read as one drawing step at its own call site, in order.
//
// No JSX list context needs a `key` prop here: every call site embeds
// each primitive's result as its own individual {expression} child in
// a fixed-order Group, never through a .map() over an array.

import React from 'react';
import { Group, Rect, Circle, Path, Text } from 'react-konva';
import {
  COLOR_OUTLINE, COLOR_LAMP_LIT,
  SITE_BAND_WIDTH, SITE_OUTLINE_WIDTH,
  SITE_CONC, SITE_BLUE, SITE_GREY,
  SITE_LED_OFF, SITE_LED_ON_GREEN, SITE_LED_HIGHLIGHT, SITE_OBJECT_PIPE_WIDTH,
  SITE_FLANGE_THICKNESS, SITE_FLANGE_SPAN, SITE_OUTLINE_WIDTH_MEDIUM,
  CONDUCTOR_OUTLINE, CONDUCTOR_SHADOW_WIDTH, CONDUCTOR_SHADOW_OFFSET_X, CONDUCTOR_SHADOW_OFFSET_Y, CONDUCTOR_SHADOW_OPACITY,
  CONDUCTOR_HIGHLIGHT_WIDTH, CONDUCTOR_HIGHLIGHT_OFFSET_X, CONDUCTOR_HIGHLIGHT_OFFSET_Y
} from '../../theme/ScadaTheme';
import type { SiteShadeTriad } from '../../theme/ScadaTheme';

export interface BandedRectOptions {
  /** Shading band thickness - 0 draws no bands at all (a plain outlined fill). Defaults to SITE_BAND_WIDTH. */
  band?: number;
  outlineWidth?: number;
}

/**
 * A rectangle with a lighter band along its own top edge and a darker
 * band along its own bottom edge - docs/EPW_rysunki_referencja.py's own
 * C.rect(). band=0 skips both bands entirely (that file's own `if
 * band:` guard - a plain outlined fill, used for a handful of small
 * indicator squares that should not read as a shaded 3D surface).
 */
export function bandedRect(
  x: number, y: number, width: number, height: number,
  triad: SiteShadeTriad, options: BandedRectOptions = {}
): React.ReactElement {
  const band = options.band ?? SITE_BAND_WIDTH;
  const ow = options.outlineWidth ?? SITE_OUTLINE_WIDTH;
  return (
    <Group>
      <Rect x={x} y={y} width={width} height={height} fill={triad.base} stroke={COLOR_OUTLINE} strokeWidth={ow} />
      {band > 0 && (
        <>
          <Rect x={x + ow / 2} y={y + ow / 2} width={width - ow} height={band} fill={triad.light} listening={false} />
          <Rect x={x + ow / 2} y={y + height - band - ow / 2} width={width - ow} height={band} fill={triad.dark} listening={false} />
        </>
      )}
    </Group>
  );
}

/**
 * A rectangle with a lighter band along its own LEFT edge and a darker
 * band along its own RIGHT edge - docs/EPW_rysunki_referencja.py's own
 * C.vrect(). Unlike bandedRect above, the reference's own vrect() has
 * no `if band:` guard at all - both side bands always draw, matching
 * that unconditionally here too (every actual vrect() call in the
 * reference passes a positive band anyway - lamp poles, tank rims).
 */
export function bandedVRect(
  x: number, y: number, width: number, height: number,
  triad: SiteShadeTriad, options: BandedRectOptions = {}
): React.ReactElement {
  const band = options.band ?? SITE_BAND_WIDTH;
  const ow = options.outlineWidth ?? SITE_OUTLINE_WIDTH;
  return (
    <Group>
      <Rect x={x} y={y} width={width} height={height} fill={triad.base} stroke={COLOR_OUTLINE} strokeWidth={ow} />
      <Rect x={x + ow / 2} y={y + ow / 2} width={band} height={height - ow} fill={triad.light} listening={false} />
      <Rect x={x + width - band - ow / 2} y={y + ow / 2} width={band} height={height - ow} fill={triad.dark} listening={false} />
    </Group>
  );
}

export interface BandedCircleOptions {
  outlineWidth?: number;
}

/**
 * A circle with a light ARC upper-left (a highlight, as if lit from
 * that direction) and a shadow arc lower-right - docs/EPW_rysunki_
 * referencja.py's own C.circ(). The arc endpoints/radius/stroke-width
 * are all fixed fractions of the circle's own radius r, taken exactly
 * from that file's own path data (M{cx-r*0.72},{cy-r*0.5}
 * A{r*0.88},{r*0.88} 0 0 1 {cx+r*0.1},{cy-r*0.86} for the light arc;
 * M{cx+r*0.62},{cy+r*0.5} A{r*0.85},{r*0.85} 0 0 1 {cx-r*0.2},{cy+r*0.85}
 * for the shadow arc) - reproduced here as literal SVG path data
 * through Konva's own Path shape (which parses the same path-data
 * grammar SVG does), the most direct, least-drift way to keep this
 * exact proportion rather than re-deriving the same arcs through some
 * other combination of Konva shapes.
 */
export function bandedCircle(
  cx: number, cy: number, r: number,
  triad: SiteShadeTriad, options: BandedCircleOptions = {}
): React.ReactElement {
  const ow = options.outlineWidth ?? SITE_OUTLINE_WIDTH;
  const lightArc = `M${cx - r * 0.72},${cy - r * 0.5} A${r * 0.88},${r * 0.88} 0 0 1 ${cx + r * 0.1},${cy - r * 0.86}`;
  const darkArc = `M${cx + r * 0.62},${cy + r * 0.5} A${r * 0.85},${r * 0.85} 0 0 1 ${cx - r * 0.2},${cy + r * 0.85}`;
  return (
    <Group>
      <Circle x={cx} y={cy} radius={r} fill={triad.base} stroke={COLOR_OUTLINE} strokeWidth={ow} />
      <Path data={lightArc} stroke={triad.light} strokeWidth={r * 0.28} lineCap="round" listening={false} />
      <Path data={darkArc} stroke={triad.dark} strokeWidth={r * 0.22} lineCap="round" listening={false} />
    </Group>
  );
}

export interface GlowOptions {
  /** Defaults to COLOR_LAMP_LIT - docs/EPW_rysunki_referencja.py's own C.glow() default is that exact same value, reused here rather than duplicated as a literal. */
  color?: string;
}

/**
 * A soft halo around a lit fixture - three concentric, unstroked
 * circles of the SAME color, radius shrinking while opacity rises
 * toward the center (r*2.6 @ 0.18, r*1.8 @ 0.28, r*1.15 @ 0.45,
 * exactly docs/EPW_rysunki_referencja.py's own C.glow()) - the one
 * deliberate translucency/gradient-like exception in this whole file:
 * a genuine light source glowing outward, not shading on a shape's own
 * surface (which stays hard-edged banded fill everywhere else).
 */
export function glow(cx: number, cy: number, r: number, options: GlowOptions = {}): React.ReactElement {
  const color = options.color ?? COLOR_LAMP_LIT;
  return (
    <Group listening={false}>
      <Circle x={cx} y={cy} radius={r * 2.6} fill={color} opacity={0.18} />
      <Circle x={cx} y={cy} radius={r * 1.8} fill={color} opacity={0.28} />
      <Circle x={cx} y={cy} radius={r * 1.15} fill={color} opacity={0.45} />
    </Group>
  );
}

// ============================================================================
// feat/water-management commit 4: docs/EPW_gospodarka_wodna_referencja.py's
// own primitives (its own class C) that have no equivalent above -
// bandedRect/bandedVRect are already identical to that file's own r()/
// vr() (same band=4/ow=2.5 defaults - reused as-is, no changes needed).
// Its own circle primitive (c()) draws only ONE arc (light, upper-left)
// where bandedCircle above draws two (light AND a dark shadow arc) -
// a genuine, deliberate difference between the two reference files'
// own conventions, not an inconsistency to paper over - so this gets
// its own function with THIS file's own exact arc fractions, rather
// than reusing bandedCircle's slightly different ones.
// ============================================================================

/**
 * A circle with ONLY a light arc upper-left, no shadow arc - docs/EPW_
 * gospodarka_wodna_referencja.py's own C.c(). Same idea as bandedCircle
 * above, deliberately reproduced with THIS file's own slightly
 * different fractions (0.7/0.5/0.85/0.1/0.85/0.3, not bandedCircle's
 * own 0.72/0.5/0.88/0.1/0.86/0.28) rather than forcing the two
 * reference files onto one shared set of numbers.
 */
export function bandedCircleLightOnly(
  cx: number, cy: number, r: number,
  triad: SiteShadeTriad, options: BandedCircleOptions = {}
): React.ReactElement {
  const ow = options.outlineWidth ?? SITE_OUTLINE_WIDTH;
  const lightArc = `M${cx - r * 0.7},${cy - r * 0.5} A${r * 0.85},${r * 0.85} 0 0 1 ${cx + r * 0.1},${cy - r * 0.85}`;
  return (
    <Group>
      <Circle x={cx} y={cy} radius={r} fill={triad.base} stroke={COLOR_OUTLINE} strokeWidth={ow} />
      <Path data={lightArc} stroke={triad.light} strokeWidth={r * 0.3} lineCap="round" listening={false} />
    </Group>
  );
}

export interface ValueFieldOptions {
  /** Defaults to COLOR_OUTLINE (black) - docs/EPW_gospodarka_wodna_referencja.py's own val() always uses black text. A device-bound reading overrides this to the same PREVIEW/MISSING shading the meter element's own row uses (MeterElementNode.tsx's own colorForRow) - see RainwaterTank2Symbol.tsx's own call site. */
  textColor?: string;
}

/**
 * A SCADA-style value readout: a light field, black outline, monospace
 * text right-aligned - docs/EPW_gospodarka_wodna_referencja.py's own
 * C.val(). Fixed 18-unit height (that file's own literal), fill
 * SITE_CONC.light (that reference's own literal fill value for val() -
 * reused directly rather than duplicated as its own hex constant, they
 * match exactly).
 */
export function valueField(x: number, y: number, width: number, text: string, options: ValueFieldOptions = {}): React.ReactElement {
  const textColor = options.textColor ?? COLOR_OUTLINE;
  return (
    <Group listening={false}>
      <Rect x={x} y={y} width={width} height={18} fill={SITE_CONC.light} stroke={COLOR_OUTLINE} strokeWidth={2} />
      <Text
        x={x} y={y + 3} width={width - 4} align="right"
        text={text} fontFamily="Consolas, DejaVu Sans Mono, monospace" fontSize={11} fontStyle="bold" fill={textColor}
      />
    </Group>
  );
}

export interface StatusLedOptions {
  /** Defaults to SITE_LED_ON_GREEN - docs/EPW_gospodarka_wodna_referencja.py's own led() default. */
  color?: string;
}

/**
 * A status LED: dark when off, lit color plus a small highlight when
 * on - docs/EPW_gospodarka_wodna_referencja.py's own C.led().
 */
export function statusLed(cx: number, cy: number, on: boolean, options: StatusLedOptions = {}): React.ReactElement {
  const color = options.color ?? SITE_LED_ON_GREEN;
  return (
    <Group listening={false}>
      <Circle x={cx} y={cy} radius={6} fill={on ? color : SITE_LED_OFF} stroke={COLOR_OUTLINE} strokeWidth={2} />
      {on && <Circle x={cx - 1.6} y={cy - 1.6} radius={2.6} fill={SITE_LED_HIGHLIGHT} />}
    </Group>
  );
}

export interface ObjectPipeSegmentOptions {
  /** Defaults to SITE_OBJECT_PIPE_WIDTH (13) - docs/EPW_gospodarka_wodna_referencja.py's own pipe_seg default. */
  width?: number;
}

/**
 * A water object's own internal pipe stub, in the SAME Houston-style
 * four-pass technique commit 3 gave the main canvas's own wires
 * (outline, fill, shadow, highlight; rounded joins/caps so a bend
 * draws its own elbow) - docs/EPW_gospodarka_wodna_referencja.py's own
 * pipe_seg(). `live` is this object's own on/off state directly (SITE_
 * BLUE when flowing, SITE_GREY when not) - not a full net resolution
 * the way ConnectionLine.tsx's own conductor is: an object's internal
 * stub has no net of its own to belong to, it simply mirrors whatever
 * state the object itself is in.
 */
export function objectPipeSegment(points: { x: number; y: number }[], live: boolean, options: ObjectPipeSegmentOptions = {}): React.ReactElement {
  const width = options.width ?? SITE_OBJECT_PIPE_WIDTH;
  const triad = live ? SITE_BLUE : SITE_GREY;
  const data = 'M' + points.map(p => `${p.x},${p.y}`).join(' L');
  return (
    <Group listening={false}>
      <Path data={data} stroke={COLOR_OUTLINE} strokeWidth={width + CONDUCTOR_OUTLINE} fill="none" lineCap="round" lineJoin="round" />
      <Path data={data} stroke={triad.base} strokeWidth={width} fill="none" lineCap="round" lineJoin="round" />
      <Path
        data={data} stroke={triad.dark} strokeWidth={CONDUCTOR_SHADOW_WIDTH} fill="none" lineCap="round" lineJoin="round"
        opacity={CONDUCTOR_SHADOW_OPACITY} x={CONDUCTOR_SHADOW_OFFSET_X} y={CONDUCTOR_SHADOW_OFFSET_Y}
      />
      <Path
        data={data} stroke={triad.light} strokeWidth={CONDUCTOR_HIGHLIGHT_WIDTH} fill="none" lineCap="round" lineJoin="round"
        x={CONDUCTOR_HIGHLIGHT_OFFSET_X} y={CONDUCTOR_HIGHLIGHT_OFFSET_Y}
      />
    </Group>
  );
}

// ============================================================================
// fix/hydraulic-connections commit 5: the hydraulic connection standard,
// docs/EPW_kolnierze_referencja.py's own stub()/flange() - a krociec
// (pipe stub) plus a kolnierz (flange) at EVERY water-medium object's
// own terminal, drawn the SAME way everywhere ("Zaden aparat nie
// rysuje wlasnego kroćca po swojemu" - this task's own words). Every
// water aparat in this library calls waterStub (or, for the handful
// whose own body does not naturally line up with the true terminal
// axis, objectPipeSegment plus waterFlange directly, with a short jog
// in between - the same technique the reference's own tank() uses for
// its DOPLYW) rather than drawing its own ad-hoc stub.
// ============================================================================

export type StubSide = 'L' | 'R' | 'T' | 'B';

export interface WaterStubOptions {
  /** Pipe core width - defaults to SITE_OBJECT_PIPE_WIDTH, same as objectPipeSegment's own default. */
  width?: number;
}

/**
 * Where a flange's own center sits for a given side and canvas size -
 * exported so a caller needing a JOGGED stub (its own body does not
 * land on the true terminal axis directly - see this section's own
 * header comment) can still place waterFlange exactly right without
 * duplicating this arithmetic.
 */
export function flangeCenterForSide(side: StubSide, alongAxis: number, canvasWidth: number, canvasHeight: number): { x: number; y: number } {
  switch (side) {
    case 'L': return { x: SITE_FLANGE_THICKNESS / 2 + 1, y: alongAxis };
    case 'R': return { x: canvasWidth - SITE_FLANGE_THICKNESS / 2 - 1, y: alongAxis };
    case 'T': return { x: alongAxis, y: SITE_FLANGE_THICKNESS / 2 + 1 };
    case 'B': return { x: alongAxis, y: canvasHeight - SITE_FLANGE_THICKNESS / 2 - 1 };
  }
}

/**
 * The kolnierz itself (reference's own flange()): a bar PERPENDICULAR
 * to the pipe's own axis, right at the canvas edge, wider than the
 * pipe (SITE_FLANGE_SPAN vs SITE_OBJECT_PIPE_WIDTH), with its own
 * light band - "z pasmem swiatla u gory albo z lewej", the reference's
 * own words, matched here by always placing the light band at the
 * flange's own top-left corner regardless of side, exactly as its own
 * flange() does (`x+1.2,y+1.2`, unconditional on side). Colored by the
 * same live/not-live rule as the pipe it terminates - never a separate
 * decision of its own.
 */
export function waterFlange(x: number, y: number, side: StubSide, live: boolean): React.ReactElement {
  const triad = live ? SITE_BLUE : SITE_GREY;
  const horizontal = side === 'L' || side === 'R';
  const w = horizontal ? SITE_FLANGE_THICKNESS : SITE_FLANGE_SPAN;
  const h = horizontal ? SITE_FLANGE_SPAN : SITE_FLANGE_THICKNESS;
  return (
    <Group listening={false}>
      <Rect x={x - w / 2} y={y - h / 2} width={w} height={h} fill={triad.base} stroke={COLOR_OUTLINE} strokeWidth={SITE_OUTLINE_WIDTH_MEDIUM} />
      {horizontal
        ? <Rect x={x - w / 2 + 1.2} y={y - h / 2 + 1.2} width={w - 2.4} height={3} fill={triad.light} />
        : <Rect x={x - w / 2 + 1.2} y={y - h / 2 + 1.2} width={3} height={h - 2.4} fill={triad.light} />}
    </Group>
  );
}

/**
 * The reference's own stub(): a krociec (objectPipeSegment) from an
 * aparat's own body-side connection point (bx,by) straight out to the
 * canvas edge on `side`, plus a kolnierz (waterFlange) right at that
 * edge - one call per water terminal. (bx,by) must already share the
 * OTHER axis with the true terminal position (e.g. by already equal
 * to canvasHeight/2 for an L/R terminal) - this is the STRAIGHT case,
 * which covers every water aparat in this library except the handful
 * whose own body sits far enough off-axis to need a short jog first
 * (see this section's own header comment).
 */
export function waterStub(bx: number, by: number, side: StubSide, live: boolean, canvasWidth: number, canvasHeight: number, options: WaterStubOptions = {}): React.ReactElement {
  const edge = side === 'L' ? { x: 0, y: by }
    : side === 'R' ? { x: canvasWidth, y: by }
    : side === 'T' ? { x: bx, y: 0 }
    : { x: bx, y: canvasHeight };
  const alongAxis = side === 'L' || side === 'R' ? by : bx;
  const flangeCenter = flangeCenterForSide(side, alongAxis, canvasWidth, canvasHeight);
  return (
    <Group listening={false}>
      {objectPipeSegment([{ x: bx, y: by }, edge], live, options)}
      {waterFlange(flangeCenter.x, flangeCenter.y, side, live)}
    </Group>
  );
}
