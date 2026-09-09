// EPW Project v2 - the second half of the platform's data contract, on
// top of the device registry (DeviceSchema.ts). Type definitions only,
// no executable logic.
//
// The rule this whole module exists to enforce: DEVICE CONFIGURATION DOES
// NOT LIVE ON A SCREEN. A screen only says "at this spot, with this
// symbol, show device KOT_KMG1" (ScreenItem.device, a bare id string).
// All behavioral configuration - inputs, outputs, commands, supervision -
// lives in the device registry (DeviceSchema.ts). The same device
// appearing on multiple screens is CORRECT: that is the entire point of
// this architecture, not an edge case to guard against.
//
// One controller = one project = one file. Projects do not reference each
// other - tying multiple controllers together is Home Assistant's job,
// not this format's.

import type { DeviceRegistry } from './DeviceSchema';

export const PROJECT_SCHEMA_VERSION_V2 = 2;
export const PROJECT_FORMAT_NAME_V2 = 'EPW_PROJECT';

// NOTE: this is a second, independent format alongside ProjectSchema.ts's
// .epwsyn (CURRENT_SCHEMA_VERSION, still 1, untouched by this file). The
// two coexist until a migration is written - not part of this module.

export interface Point {
  x: number;
  y: number;
}

// ---- Backdrop layer -----------------------------------------------------
// The backdrop sits UNDER the devices. It has no ports, no tags, no
// state - to EPW-OS it is graphics only.

export interface WallElement {
  id: string;
  type: 'WALL';
  from: Point;
  to: Point;
}
// A wall has exactly one kind. No thickness, style, kind or material
// field - deliberately left out.

export interface RoomElement {
  id: string;
  type: 'ROOM';
  points: Point[]; // minimum 3
  name: string;
}

export interface TextElement {
  id: string;
  type: 'TEXT';
  x: number;
  y: number;
  text: string;
  fontSize: number;
}

export interface FrameElement {
  id: string;
  type: 'FRAME';
  x: number;
  y: number;
  width: number;
  height: number;
  label?: string;
}

export type BackdropElement = WallElement | RoomElement | TextElement | FrameElement;

// ---- Screen item (a symbol placed on the canvas) -------------------------

export interface ScreenItem {
  id: string;
  device?: string; // a device id from the device registry. Absent = pure graphics, no device.
  symbol: string;  // symbol identifier from the symbol library
  x: number;
  y: number;
  rotation: number;
  label: {
    showDesignation: boolean;
    showName: boolean;
    position: 'TOP' | 'BOTTOM' | 'LEFT' | 'RIGHT';
  };
}
// CRITICAL: ScreenItem does not and must not carry any behavioral device
// configuration - no inputs, outputs, commands, timings, tags or bindings,
// no feedback modes. Only position, symbol and label. If a field seems
// like it might fit here, it does not.

// ---- Navigation between screens -------------------------------------------

export interface NavigationLink {
  id: string;
  x: number;
  y: number;
  label: string;        // '-> Kotlownia'
  targetScreen: string; // id of the target screen
}

// ---- Connection on a screen -----------------------------------------------

export interface ScreenConnection {
  id: string;
  fromItem: string;
  fromPort: string;
  toItem: string;
  toPort: string;
  type: string;
  waypoints?: Point[]; // kept deliberately - a routing tool will come later
}

// ---- Screen ---------------------------------------------------------------

export interface Screen {
  id: string;
  name: string;
  group?: string; // optional, ONE LEVEL, no nesting. Absent = ungrouped screen.
  isMain: boolean;
  canvas: { width: number; height: number; background: string; gridSize: number };
  backdrop: BackdropElement[];
  items: ScreenItem[];
  connections: ScreenConnection[];
  navigation: NavigationLink[];
}
// No group nesting, no group tree, no parent-group field. A group is
// plain text, one level.

// ---- Project ---------------------------------------------------------------

export interface EpwProjectV2 {
  format: 'EPW_PROJECT';
  schema_version: 2;
  project: { name: string; description: string; created_at: string; modified_at: string };
  controller: { id: string; name: string; hardware: string }; // id: A-Z and 0-9 only
  symbolLibrary: string;
  devices: DeviceRegistry;
  screens: Screen[]; // no limit on the number of screens
}
