// feat/room-plan: the floor under the walls, plus the pools of light
// the lit luminaires cast on it.
//
// Drawn as ONE component, below every wall, symbol and wire, because
// the two belong together: a light pool is only meaningful on a floor,
// and both are derived - neither is an element the user places or can
// select. Nothing here is interactive (listening={false} throughout),
// so the floor can never swallow a click meant for what stands on it.
//
// The floor polygons come from RoomFloors.ts (walls that enclose an
// area get a floor); the material comes from the screen's own canvas
// config. See RoomFloors.ts's header for why only simple closed loops
// are filled.

import React from 'react';
import { Circle, Group, Line } from 'react-konva';
import type { WallElement } from '../elements/WallElement';
import type { SynopticObject } from '../store';
import { useStore } from '../store';
import { findClosedRooms, roomToPoints } from '../project/RoomFloors';
import { getFloorMaterial, getMaterialTile, shade } from '../theme/Materials';
import type { FloorMaterialId } from '../theme/Materials';
import { COLOR_LAMP_LIT } from '../theme/ScadaTheme';

export interface RoomFloorLayerProps {
  walls: WallElement[];
  objects: SynopticObject[];
  floorMaterial: FloorMaterialId | undefined;
}

// A lit luminaire throws a pool roughly this many times its own size.
// Big enough that two fixtures in a room overlap into even light,
// small enough that one fixture does not flood a whole floor.
//
// Sized from the fixture's MEAN dimension, not its largest: a 120 cm
// fluorescent batten is long and narrow, and taking its length would
// give it a pool three metres across - it would wash out the whole
// room. The mean keeps a batten's pool wider than a downlight's
// without letting its length run away.
const LIGHT_POOL_FACTOR = 2.6;
const LIGHT_POOL_OPACITY = 0.38;

// The contact shadow along the walls - see where it is drawn below.
const ROOM_SHADOW_WIDTH = 14;
const ROOM_SHADOW_OPACITY = 0.13;

export const RoomFloorLayer: React.FC<RoomFloorLayerProps> = ({ walls, objects, floorMaterial }) => {
  // feat/live-view: a luminaire lit on the controller lights the floor too.
  const liveStates = useStore(s => s.liveStates);
  const rooms = findClosedRooms(walls);
  if (rooms.length === 0) return null;

  const material = getFloorMaterial(floorMaterial);
  const tile = getMaterialTile(material);
  // Flat color when there is no DOM to build a tile on - never the
  // canvas background, which is exactly the see-through look this
  // layer exists to remove.
  const fillProps = tile
    ? { fillPatternImage: tile as unknown as HTMLImageElement, fillPatternRepeat: 'repeat' }
    : { fill: material.base };

  // Every luminaire TYPE, not just the flush ceiling one: the prefix
  // covers plafon/pendant/wall/fluorescent/halogen, so a lighting type
  // added later casts a pool without this needing to be remembered.
  // (The first version of this listed one type by name, which is
  // exactly why the four newer fittings lit up but left the floor
  // dark.)
  const litLuminaires = objects.filter(
    o => o.type.startsWith('building.luminaire') && (liveStates[o.id] ?? o.editor?.preview_state) === 'ON'
  );

  return (
    <Group listening={false}>
      {rooms.map((room, i) => (
        <React.Fragment key={`floor-${i}`}>
          <Line
            points={roomToPoints(room)}
            closed
            {...fillProps}
            // A hairline darker than the material itself, so two floors
            // meeting along a shared wall still read as two rooms.
            stroke={shade(material.base, 0.75)}
            strokeWidth={1}
            listening={false}
          />
          {/* Contact shadow where the floor meets the walls. A thick,
              very transparent stroke on the same polygon: half of it
              falls inside the room and reads as the wall's own shadow,
              the outer half lands under the wall body that is drawn
              over this layer, so it never shows. Cheapest possible
              ambient occlusion, and it is what stops the floor looking
              like a flat sticker inside a flat outline. */}
          <Line
            points={roomToPoints(room)}
            closed
            stroke="#000000"
            strokeWidth={ROOM_SHADOW_WIDTH}
            opacity={ROOM_SHADOW_OPACITY}
            listening={false}
          />
        </React.Fragment>
      ))}

      {/* Light pools. Drawn after the floors so they lie ON the
          material, and clipped to nothing in particular on purpose:
          spill past a wall is what a real fixture near a doorway does,
          and clipping every pool to its room would cost a
          point-in-polygon test per fixture per frame for a detail
          nobody would miss. */}
      {litLuminaires.map(lamp => {
        const radius = ((lamp.width + lamp.height) / 2) * LIGHT_POOL_FACTOR;
        return (
          <Circle
            key={`pool-${lamp.id}`}
            x={lamp.x + lamp.width / 2}
            y={lamp.y + lamp.height / 2}
            radius={radius}
            fillRadialGradientStartPoint={{ x: 0, y: 0 }}
            fillRadialGradientStartRadius={0}
            fillRadialGradientEndPoint={{ x: 0, y: 0 }}
            fillRadialGradientEndRadius={radius}
            fillRadialGradientColorStops={[0, COLOR_LAMP_LIT, 1, 'rgba(255,232,0,0)']}
            opacity={LIGHT_POOL_OPACITY}
            listening={false}
          />
        );
      })}
    </Group>
  );
};
