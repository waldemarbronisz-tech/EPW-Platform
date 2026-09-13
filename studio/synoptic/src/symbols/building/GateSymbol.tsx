// feat/room-plan: powered vehicle gate (brama wjazdowa z napedem), plan
// view.
//
// The only opening on this plan that MOVES, and the reason it has a
// state at all: a gate with a drive is a controlled device like any
// luminaire, so it goes on a circuit, it is switched from the same
// Podglad click, and it can be wired to a real controller output
// (project/CircuitBindings.ts). Everything else in the openings group is
// joinery; this one is plant.
//
// CLOSED draws the two leaves meeting across the opening. OPEN swings
// them back against their posts and leaves the sweep arcs showing -
// which is also what tells you, on a plan, how much clear space the
// gate needs before you park something in it.
//
// The drive itself is drawn as a small unit beside the hinge post: a
// gate with a motor and a gate without one are different things to
// order, and the plan should say which this is.
//
// Scale: 300 cm clear opening (Scale.ts).

import React from 'react';
import { Arc, Group, Line, Rect } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { COLOR_OUTLINE, METAL, METAL_DARK, PLAN_SHADOW, symbolStroke } from './BuildingSymbolTheme';
import { COLOR_RUN } from '../../theme/ScadaTheme';

export type GateState = 'CLOSED' | 'OPEN';
// oxlint-disable-next-line react/only-export-components -- one file per symbol is required; this state list belongs beside its component.
export const GATE_STATES: GateState[] = ['CLOSED', 'OPEN'];

// One infill bar per this many pixels, so a gate stretched to 5 m gains
// bars instead of stretching the ones it has.
const PIXELS_PER_BAR = 20;

// How far a leaf swings. Not a full 90 degrees: a real leaf stops
// against its own post, and drawing it flush with the wall would make
// an open gate indistinguishable from no gate at all.
const OPEN_ANGLE = 82;

/** One leaf, drawn from its hinge. Rotation is applied by the Group, so the leaf geometry itself is identical open or closed - which is what keeps the two states obviously the same object. */
const GateLeaf: React.FC<{
  length: number;
  thickness: number;
  bars: number;
  stroke: number;
}> = ({ length, thickness, bars, stroke }) => (
  <>
    <Rect
      width={length}
      height={thickness}
      fill={METAL}
      stroke={COLOR_OUTLINE}
      strokeWidth={stroke}
      {...PLAN_SHADOW}
    />
    {Array.from({ length: bars }, (_, i) => {
      const x = (length * (i + 1)) / (bars + 1);
      return (
        <Line
          key={i}
          points={[x, 0, x, thickness]}
          stroke={METAL_DARK}
          strokeWidth={stroke * 0.8}
          listening={false}
        />
      );
    })}
  </>
);

export const GateSymbol: React.FC<SymbolProps> = ({ obj, state }) => {
  const w = obj.width;
  const h = obj.height;
  const stroke = symbolStroke(w, h);
  const isOpen = state === 'OPEN';

  const postWidth = Math.max(3, h * 0.28);
  const leafThickness = Math.max(2, h * 0.34);
  const leafLength = w / 2;
  // Hinges sit on the inner face of each post, on the gate's own centre
  // line, so a leaf sweeps about the point it is actually hung from.
  const hingeY = h / 2;
  const barsPerLeaf = Math.max(1, Math.floor(leafLength / PIXELS_PER_BAR) - 1);

  return (
    <Group>
      {/* Sweep arcs - shown only when open, where they answer "how much
          room does this need". On a closed gate they would be clutter. */}
      {isOpen && (
        <>
          <Arc
            x={0} y={hingeY}
            innerRadius={leafLength} outerRadius={leafLength}
            angle={OPEN_ANGLE} rotation={0}
            stroke={COLOR_OUTLINE} strokeWidth={stroke * 0.55}
            dash={[5, 4]} opacity={0.6} listening={false}
          />
          <Arc
            x={w} y={hingeY}
            innerRadius={leafLength} outerRadius={leafLength}
            angle={OPEN_ANGLE} rotation={180 - OPEN_ANGLE}
            stroke={COLOR_OUTLINE} strokeWidth={stroke * 0.55}
            dash={[5, 4]} opacity={0.6} listening={false}
          />
        </>
      )}

      {/* Left leaf: hinged at x=0, running right when closed, swung
          down-left when open. */}
      <Group
        x={0}
        y={hingeY - leafThickness / 2}
        rotation={isOpen ? OPEN_ANGLE : 0}
      >
        <GateLeaf length={leafLength} thickness={leafThickness} bars={barsPerLeaf} stroke={stroke} />
      </Group>

      {/* Right leaf: hinged at x=w, running left when closed (drawn
          rotated 180) and swung down-right when open. */}
      <Group
        x={w}
        y={hingeY + leafThickness / 2}
        rotation={isOpen ? 180 - OPEN_ANGLE : 180}
      >
        <GateLeaf length={leafLength} thickness={leafThickness} bars={barsPerLeaf} stroke={stroke} />
      </Group>

      {/* Posts, over the leaves so the hinge end always reads as held. */}
      <Rect
        x={-postWidth / 2} y={0} width={postWidth} height={h}
        fill={METAL_DARK} stroke={COLOR_OUTLINE} strokeWidth={stroke}
      />
      <Rect
        x={w - postWidth / 2} y={0} width={postWidth} height={h}
        fill={METAL_DARK} stroke={COLOR_OUTLINE} strokeWidth={stroke}
      />

      {/* The drive, beside the left post. Green while the gate is open -
          the same COLOR_RUN this platform uses for "running" everywhere
          else, so a powered gate reads like every other running thing on
          the screen rather than inventing its own vocabulary. */}
      <Rect
        x={-postWidth * 1.9}
        y={hingeY - h * 0.22}
        width={postWidth * 1.2}
        height={h * 0.44}
        fill={isOpen ? COLOR_RUN : METAL}
        stroke={COLOR_OUTLINE}
        strokeWidth={stroke}
        cornerRadius={stroke}
      />
      {/* Drive shaft to the post. */}
      <Line
        points={[-postWidth * 0.7, hingeY, -postWidth / 2, hingeY]}
        stroke={COLOR_OUTLINE}
        strokeWidth={stroke * 1.2}
        listening={false}
      />
    </Group>
  );
};
