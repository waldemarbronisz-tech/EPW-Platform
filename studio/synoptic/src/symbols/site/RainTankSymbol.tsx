// feat/site-objects-2d commit 2 - "4. Zbiornik na deszczowke" from
// docs/EPW_rysunki_referencja.py's own zbiornik(on). Top view: a
// circular tank with a visible water level inside, a center cap, a
// side spigot (krolec). ZALACZONY - high level; WYLACZONY - low.
//
// The reference draws the water level through an SVG clipPath (a
// rectangle whose height tracks the fill level, clipped to the tank's
// own inner circle so it never spills past the rim) - translated here
// to Konva's own Group clipFunc, the same clipping mechanism
// FrameElementNode.tsx's own roof-hatching already uses.

import React from 'react';
import { Group, Circle, Rect } from 'react-konva';
import type { SymbolProps } from '../SymbolRenderer';
import { bandedCircle, waterFlange, flangeCenterForSide, objectPipeSegment } from './BandedShading';
import { resolveSiteState } from './SiteSymbolState';
import {
  COLOR_OUTLINE, SITE_GREY, SITE_DGREY, SITE_BLUE,
  SITE_OUTLINE_WIDTH_MEDIUM, SITE_CANVAS_SCALE
} from '../../theme/ScadaTheme';

export type RainTankState = 'ZALACZONY' | 'WYLACZONY';
// oxlint-disable-next-line react/only-export-components -- one file per symbol, same convention as scada/ symbols.
export const RAIN_TANK_STATES: RainTankState[] = ['ZALACZONY', 'WYLACZONY'];

const CX = 80, CY = 64;

export const RainTankSymbol: React.FC<SymbolProps> = ({ state, terminalNetState }) => {
  const on = resolveSiteState(state, RAIN_TANK_STATES, 'WYLACZONY') === 'ZALACZONY';
  const level = on ? 0.68 : 0.22;
  const height = Math.floor(62 * level);
  const krociecLive = (terminalNetState?.('KROCIEC') ?? 'INACTIVE') === 'ACTIVE';

  return (
    // SITE_CANVAS_SCALE - see HouseSymbol.tsx's own comment on this
    // same wrapper for the full reasoning. The clipFunc below reads
    // CX/CY/33 in this SAME pre-scale local space - Konva composes the
    // nested Group's transform with this outer one automatically, so
    // the clip needs no adjustment of its own.
    <Group scaleX={SITE_CANVAS_SCALE} scaleY={SITE_CANVAS_SCALE}>
      {bandedCircle(CX, CY, 44, SITE_GREY)}
      <Circle x={CX} y={CY} radius={34} stroke={SITE_DGREY.base} strokeWidth={SITE_OUTLINE_WIDTH_MEDIUM} listening={false} />
      <Group clipFunc={(ctx: any) => { ctx.arc(CX, CY, 33, 0, Math.PI * 2); }} listening={false}>
        <Rect x={47} y={95 - height} width={66} height={height} fill={SITE_BLUE.base} />
        <Rect x={47} y={95 - height} width={66} height={5} fill={SITE_BLUE.light} />
      </Group>
      <Circle x={CX} y={CY} radius={33} stroke={COLOR_OUTLINE} strokeWidth={SITE_OUTLINE_WIDTH_MEDIUM} listening={false} />
      {bandedCircle(CX, CY, 11, SITE_DGREY, { outlineWidth: SITE_OUTLINE_WIDTH_MEDIUM })}
      {/* fix/hydraulic-connections commit 5: krociec+kolnierz on the
          one terminal (KROCIEC, RIGHT) - the true terminal (local
          160,60, in this file's own pre-scale 160x120 space) does not
          share the tank's own vertical center (CY=64), so the pipe
          jogs from the tank's own rim (124,64) over to the target
          axis before running straight out to the edge - the same
          technique the reference's own tank() uses for its DOPLYW.
          Retires the old plain decorative spigot rect, which never
          reached the true edge at all (stopped at x=152, 8 short). */}
      {objectPipeSegment([{ x: 124, y: 64 }, { x: 145, y: 64 }, { x: 145, y: 60 }, { x: 160, y: 60 }], krociecLive)}
      {waterFlange(flangeCenterForSide('R', 60, 160, 120).x, 60, 'R', krociecLive)}
    </Group>
  );
};
