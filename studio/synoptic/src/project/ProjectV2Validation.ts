// Validation for EPW Project v2 (ProjectV2Schema.ts). Pure functions, no
// side effects, no dependency on the app store.
//
// validateProjectV2 takes unknown, not EpwProjectV2: it validates JSON
// loaded from disk, not an already-trusted object. Shape is checked first,
// item by item, exactly like DeviceValidation.ts's own shape-validation
// pass (this file deliberately mirrors that pattern): anything with the
// wrong shape is reported once and excluded from the business-rule checks
// below, instead of cascading secondary errors or throwing. The validator
// must never throw on any input.
//
// EVERY violation is an ERROR, never a WARNING - same reasoning as
// DeviceValidation.ts: this format is a contract between three
// applications.
//
// The device registry embedded in a project is validated by delegating to
// validateDeviceRegistry - its rules are not duplicated here.

import type { ValidationIssue, ValidationResult } from './DeviceValidation';
import { validateDeviceRegistry } from './DeviceValidation';
import { type BackdropElement, type NavigationLink, type Point, type Screen, type ScreenConnection, type ScreenItem } from './ProjectV2Schema';
import { PROJECT_FORMAT_NAME_V2, PROJECT_SCHEMA_VERSION_V2 } from './ProjectV2Schema';

// ---- shape primitives -----------------------------------------------------
// Duplicated from DeviceValidation.ts rather than imported: that file is
// not modified by this task, and these are not part of its public API.

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isString(value: unknown): value is string {
  return typeof value === 'string';
}

function isBoolean(value: unknown): value is boolean {
  return typeof value === 'boolean';
}

// NaN and Infinity both satisfy `typeof x === 'number'` - Number.isFinite
// is what actually rejects them.
function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

function isPointShape(value: unknown): value is Point {
  return isPlainObject(value) && isFiniteNumber(value.x) && isFiniteNumber(value.y);
}

const BACKDROP_TYPES = ['WALL', 'ROOM', 'TEXT', 'FRAME'];
const LABEL_POSITIONS = ['TOP', 'BOTTOM', 'LEFT', 'RIGHT'];

// ---- shape validation, one item at a time ----------------------------------

function validateBackdropElementShape(raw: unknown, screenId: string, index: number, issues: ValidationIssue[]): BackdropElement | null {
  if (!isPlainObject(raw)) {
    issues.push({ severity: 'ERROR', code: 'BACKDROP_INVALID_SHAPE', message: `Screen '${screenId}': backdrop element at index ${index} must be an object` });
    return null;
  }

  const idForMessages = isString(raw.id) ? raw.id : `#${index}`;
  const problems: string[] = [];
  if (!isString(raw.id)) problems.push('id must be a string');

  if (!BACKDROP_TYPES.includes(raw.type as string)) {
    issues.push({ severity: 'ERROR', code: 'BACKDROP_UNKNOWN_TYPE', message: `Screen '${screenId}', backdrop element '${idForMessages}': unknown type '${String(raw.type)}', expected one of WALL, ROOM, TEXT, FRAME` });
    return null;
  }

  switch (raw.type as 'WALL' | 'ROOM' | 'TEXT' | 'FRAME') {
    case 'WALL':
      if (!isPointShape(raw.from)) problems.push('from must be a {x, y} point');
      if (!isPointShape(raw.to)) problems.push('to must be a {x, y} point');
      break;
    case 'ROOM':
      if (!Array.isArray(raw.points) || !raw.points.every(isPointShape)) problems.push('points must be an array of {x, y} points');
      if (!isString(raw.name)) problems.push('name must be a string');
      break;
    case 'TEXT':
      if (!isFiniteNumber(raw.x)) problems.push('x must be a finite number');
      if (!isFiniteNumber(raw.y)) problems.push('y must be a finite number');
      if (!isString(raw.text)) problems.push('text must be a string');
      if (!isFiniteNumber(raw.fontSize)) problems.push('fontSize must be a finite number');
      break;
    case 'FRAME':
      if (!isFiniteNumber(raw.x)) problems.push('x must be a finite number');
      if (!isFiniteNumber(raw.y)) problems.push('y must be a finite number');
      if (!isFiniteNumber(raw.width)) problems.push('width must be a finite number');
      if (!isFiniteNumber(raw.height)) problems.push('height must be a finite number');
      if (raw.label !== undefined && !isString(raw.label)) problems.push('label must be a string if present');
      break;
  }

  if (problems.length > 0) {
    issues.push({ severity: 'ERROR', code: 'BACKDROP_INVALID_SHAPE', message: `Screen '${screenId}', backdrop element '${idForMessages}': ${problems.join('; ')}` });
    return null;
  }

  return raw as unknown as BackdropElement;
}

function validateScreenItemShape(raw: unknown, screenId: string, index: number, issues: ValidationIssue[]): ScreenItem | null {
  if (!isPlainObject(raw)) {
    issues.push({ severity: 'ERROR', code: 'SCREEN_ITEM_INVALID_SHAPE', message: `Screen '${screenId}': item at index ${index} must be an object` });
    return null;
  }

  const idForMessages = isString(raw.id) ? raw.id : `#${index}`;
  const problems: string[] = [];
  if (!isString(raw.id)) problems.push('id must be a string');
  if (raw.device !== undefined && !isString(raw.device)) problems.push('device must be a string if present');
  if (!isString(raw.symbol)) problems.push('symbol must be a string');
  if (!isFiniteNumber(raw.x)) problems.push('x must be a finite number');
  if (!isFiniteNumber(raw.y)) problems.push('y must be a finite number');
  if (!isFiniteNumber(raw.rotation)) problems.push('rotation must be a finite number');

  const labelOk = isPlainObject(raw.label);
  if (!labelOk) {
    problems.push('label must be an object');
  } else {
    const label = raw.label as Record<string, unknown>;
    if (!isBoolean(label.showDesignation)) problems.push('label.showDesignation must be a boolean');
    if (!isBoolean(label.showName)) problems.push('label.showName must be a boolean');
    if (!LABEL_POSITIONS.includes(label.position as string)) problems.push("label.position must be one of 'TOP','BOTTOM','LEFT','RIGHT'");
  }

  if (problems.length > 0) {
    issues.push({ severity: 'ERROR', code: 'SCREEN_ITEM_INVALID_SHAPE', message: `Screen '${screenId}', item '${idForMessages}': ${problems.join('; ')}` });
    return null;
  }

  return raw as unknown as ScreenItem;
}

function validateScreenConnectionShape(raw: unknown, screenId: string, index: number, issues: ValidationIssue[]): ScreenConnection | null {
  if (!isPlainObject(raw)) {
    issues.push({ severity: 'ERROR', code: 'SCREEN_CONNECTION_INVALID_SHAPE', message: `Screen '${screenId}': connection at index ${index} must be an object` });
    return null;
  }

  const idForMessages = isString(raw.id) ? raw.id : `#${index}`;
  const problems: string[] = [];
  if (!isString(raw.id)) problems.push('id must be a string');
  if (!isString(raw.fromItem)) problems.push('fromItem must be a string');
  if (!isString(raw.fromPort)) problems.push('fromPort must be a string');
  if (!isString(raw.toItem)) problems.push('toItem must be a string');
  if (!isString(raw.toPort)) problems.push('toPort must be a string');
  if (!isString(raw.type)) problems.push('type must be a string');
  if (raw.waypoints !== undefined && (!Array.isArray(raw.waypoints) || !raw.waypoints.every(isPointShape))) {
    problems.push('waypoints must be an array of {x, y} points if present');
  }

  if (problems.length > 0) {
    issues.push({ severity: 'ERROR', code: 'SCREEN_CONNECTION_INVALID_SHAPE', message: `Screen '${screenId}', connection '${idForMessages}': ${problems.join('; ')}` });
    return null;
  }

  return raw as unknown as ScreenConnection;
}

function validateNavigationLinkShape(raw: unknown, screenId: string, index: number, issues: ValidationIssue[]): NavigationLink | null {
  if (!isPlainObject(raw)) {
    issues.push({ severity: 'ERROR', code: 'NAVIGATION_INVALID_SHAPE', message: `Screen '${screenId}': navigation link at index ${index} must be an object` });
    return null;
  }

  const idForMessages = isString(raw.id) ? raw.id : `#${index}`;
  const problems: string[] = [];
  if (!isString(raw.id)) problems.push('id must be a string');
  if (!isFiniteNumber(raw.x)) problems.push('x must be a finite number');
  if (!isFiniteNumber(raw.y)) problems.push('y must be a finite number');
  if (!isString(raw.label)) problems.push('label must be a string');
  if (!isString(raw.targetScreen)) problems.push('targetScreen must be a string');

  if (problems.length > 0) {
    issues.push({ severity: 'ERROR', code: 'NAVIGATION_INVALID_SHAPE', message: `Screen '${screenId}', navigation link '${idForMessages}': ${problems.join('; ')}` });
    return null;
  }

  return raw as unknown as NavigationLink;
}

function validateScreenShape(raw: unknown, index: number, issues: ValidationIssue[]): Screen | null {
  if (!isPlainObject(raw)) {
    issues.push({ severity: 'ERROR', code: 'SCREEN_INVALID_SHAPE', message: `Screen at index ${index} must be an object` });
    return null;
  }

  const idForMessages = isString(raw.id) ? raw.id : `#${index}`;
  const problems: string[] = [];
  if (!isString(raw.id)) problems.push('id must be a string');
  if (!isString(raw.name)) problems.push('name must be a string');
  if (raw.group !== undefined && !isString(raw.group)) problems.push('group must be a string if present');
  if (!isBoolean(raw.isMain)) problems.push('isMain must be a boolean');

  const canvasOk = isPlainObject(raw.canvas);
  if (!canvasOk) {
    problems.push('canvas must be an object');
  } else {
    const canvas = raw.canvas as Record<string, unknown>;
    if (!isFiniteNumber(canvas.width)) problems.push('canvas.width must be a finite number');
    if (!isFiniteNumber(canvas.height)) problems.push('canvas.height must be a finite number');
    if (!isString(canvas.background)) problems.push('canvas.background must be a string');
    if (!isFiniteNumber(canvas.gridSize)) problems.push('canvas.gridSize must be a finite number');
  }

  const backdropOk = Array.isArray(raw.backdrop);
  const itemsOk = Array.isArray(raw.items);
  const connectionsOk = Array.isArray(raw.connections);
  const navigationOk = Array.isArray(raw.navigation);
  if (!backdropOk) problems.push('backdrop must be an array');
  if (!itemsOk) problems.push('items must be an array');
  if (!connectionsOk) problems.push('connections must be an array');
  if (!navigationOk) problems.push('navigation must be an array');

  if (problems.length > 0) {
    issues.push({ severity: 'ERROR', code: 'SCREEN_INVALID_SHAPE', message: `Screen '${idForMessages}': ${problems.join('; ')}` });
    return null;
  }

  const screenId = raw.id as string;
  const backdrop = (raw.backdrop as unknown[])
    .map((r, i) => validateBackdropElementShape(r, screenId, i, issues))
    .filter((b): b is BackdropElement => b !== null);
  const items = (raw.items as unknown[])
    .map((r, i) => validateScreenItemShape(r, screenId, i, issues))
    .filter((it): it is ScreenItem => it !== null);
  const connections = (raw.connections as unknown[])
    .map((r, i) => validateScreenConnectionShape(r, screenId, i, issues))
    .filter((c): c is ScreenConnection => c !== null);
  const navigation = (raw.navigation as unknown[])
    .map((r, i) => validateNavigationLinkShape(r, screenId, i, issues))
    .filter((n): n is NavigationLink => n !== null);

  return {
    id: screenId,
    name: raw.name as string,
    group: raw.group as string | undefined,
    isMain: raw.isMain as boolean,
    canvas: raw.canvas as Screen['canvas'],
    backdrop,
    items,
    connections,
    navigation
  };
}

/**
 * Validates a whole EPW Project v2 loaded from an untrusted source (JSON
 * from disk). Shape is checked first, item by item; anything with the
 * wrong shape is reported once and excluded from the business-rule checks
 * below. The device registry section is validated by delegating to
 * validateDeviceRegistry - its rules are not duplicated here.
 */
export function validateProjectV2(project: unknown): ValidationResult {
  const issues: ValidationIssue[] = [];

  if (!isPlainObject(project)) {
    issues.push({ severity: 'ERROR', code: 'PROJECT_INVALID_SHAPE', message: 'Project must be an object' });
    return { valid: false, issues };
  }

  // ---- header ----
  if (project.format !== PROJECT_FORMAT_NAME_V2) {
    issues.push({ severity: 'ERROR', code: 'PROJECT_INVALID_FORMAT', message: `format must be '${PROJECT_FORMAT_NAME_V2}'` });
  }
  if (project.schema_version !== PROJECT_SCHEMA_VERSION_V2) {
    issues.push({ severity: 'ERROR', code: 'PROJECT_INVALID_SCHEMA_VERSION', message: `schema_version must be ${PROJECT_SCHEMA_VERSION_V2}` });
  }

  if (!isPlainObject(project.project)) {
    issues.push({ severity: 'ERROR', code: 'PROJECT_INVALID_META', message: 'project must be an object' });
  } else {
    const meta = project.project as Record<string, unknown>;
    if (!isString(meta.name) || meta.name.trim().length === 0) {
      issues.push({ severity: 'ERROR', code: 'PROJECT_EMPTY_NAME', message: 'project.name must not be empty' });
    }
  }

  if (!isPlainObject(project.controller)) {
    issues.push({ severity: 'ERROR', code: 'CONTROLLER_INVALID_SHAPE', message: 'controller must be an object' });
  } else {
    const controller = project.controller as Record<string, unknown>;
    if (!isString(controller.id) || !/^[A-Z0-9]+$/.test(controller.id)) {
      issues.push({ severity: 'ERROR', code: 'CONTROLLER_INVALID_ID', message: 'controller.id must be a non-empty string containing only A-Z and 0-9' });
    }
  }

  // ---- device registry: delegate entirely, do not duplicate its rules ----
  const deviceResult = validateDeviceRegistry(project.devices);
  issues.push(...deviceResult.issues);

  // Harvest shape-valid device ids defensively (project.devices may itself
  // be malformed - already reported above) so screen items can be
  // cross-referenced against real devices.
  const knownDeviceIds = new Set<string>();
  if (isPlainObject(project.devices) && Array.isArray((project.devices as Record<string, unknown>).devices)) {
    for (const d of (project.devices as Record<string, unknown>).devices as unknown[]) {
      if (isPlainObject(d) && isString(d.id)) knownDeviceIds.add(d.id);
    }
  }

  // ---- screens: shape pass ----
  const screensOk = Array.isArray(project.screens);
  if (!screensOk) {
    issues.push({ severity: 'ERROR', code: 'PROJECT_INVALID_SCREENS', message: 'screens must be an array' });
  }

  const screens: Screen[] = screensOk
    ? (project.screens as unknown[]).map((raw, i) => validateScreenShape(raw, i, issues)).filter((s): s is Screen => s !== null)
    : [];

  // ---- screen-level rules (id uniqueness, isMain count, canvas, name/group) ----
  const seenScreenIds = new Set<string>();
  let mainCount = 0;

  for (const screen of screens) {
    if (seenScreenIds.has(screen.id)) {
      issues.push({ severity: 'ERROR', code: 'SCREEN_DUPLICATE_ID', message: `Duplicate screen id '${screen.id}'` });
    }
    seenScreenIds.add(screen.id);

    if (screen.name.trim().length === 0) {
      issues.push({ severity: 'ERROR', code: 'SCREEN_EMPTY_NAME', message: `Screen '${screen.id}': name must not be empty` });
    }

    if (screen.group !== undefined && screen.group.trim().length === 0) {
      issues.push({ severity: 'ERROR', code: 'SCREEN_EMPTY_GROUP', message: `Screen '${screen.id}': group must not be an empty string if present` });
    }

    if (screen.isMain) mainCount++;

    if (!(screen.canvas.width > 0)) {
      issues.push({ severity: 'ERROR', code: 'SCREEN_INVALID_CANVAS_WIDTH', message: `Screen '${screen.id}': canvas.width must be greater than zero` });
    }
    if (!(screen.canvas.height > 0)) {
      issues.push({ severity: 'ERROR', code: 'SCREEN_INVALID_CANVAS_HEIGHT', message: `Screen '${screen.id}': canvas.height must be greater than zero` });
    }
    if (!(screen.canvas.gridSize > 0)) {
      issues.push({ severity: 'ERROR', code: 'SCREEN_INVALID_CANVAS_GRIDSIZE', message: `Screen '${screen.id}': canvas.gridSize must be greater than zero` });
    }
  }

  if (mainCount === 0) {
    issues.push({ severity: 'ERROR', code: 'PROJECT_NO_MAIN_SCREEN', message: 'Exactly one screen must have isMain true; found none' });
  } else if (mainCount > 1) {
    issues.push({ severity: 'ERROR', code: 'PROJECT_MULTIPLE_MAIN_SCREENS', message: `Exactly one screen must have isMain true; found ${mainCount}` });
  }

  // ---- per-screen content rules ----
  for (const screen of screens) {
    const seenBackdropIds = new Set<string>();
    for (const el of screen.backdrop) {
      if (seenBackdropIds.has(el.id)) {
        issues.push({ severity: 'ERROR', code: 'BACKDROP_DUPLICATE_ID', message: `Screen '${screen.id}': duplicate backdrop element id '${el.id}'` });
      }
      seenBackdropIds.add(el.id);

      switch (el.type) {
        case 'WALL':
          if (el.from.x === el.to.x && el.from.y === el.to.y) {
            issues.push({ severity: 'ERROR', code: 'WALL_ZERO_LENGTH', message: `Screen '${screen.id}', wall '${el.id}': from and to must not be identical` });
          }
          break;
        case 'ROOM':
          if (el.points.length < 3) {
            issues.push({ severity: 'ERROR', code: 'ROOM_TOO_FEW_POINTS', message: `Screen '${screen.id}', room '${el.id}': points must contain at least 3 points` });
          }
          if (el.name.trim().length === 0) {
            issues.push({ severity: 'ERROR', code: 'ROOM_EMPTY_NAME', message: `Screen '${screen.id}', room '${el.id}': name must not be empty` });
          }
          break;
        case 'TEXT':
          if (el.text.trim().length === 0) {
            issues.push({ severity: 'ERROR', code: 'TEXT_EMPTY', message: `Screen '${screen.id}', text '${el.id}': text must not be empty` });
          }
          if (!(el.fontSize > 0)) {
            issues.push({ severity: 'ERROR', code: 'TEXT_INVALID_FONT_SIZE', message: `Screen '${screen.id}', text '${el.id}': fontSize must be greater than zero` });
          }
          break;
        case 'FRAME':
          if (!(el.width > 0)) {
            issues.push({ severity: 'ERROR', code: 'FRAME_INVALID_WIDTH', message: `Screen '${screen.id}', frame '${el.id}': width must be greater than zero` });
          }
          if (!(el.height > 0)) {
            issues.push({ severity: 'ERROR', code: 'FRAME_INVALID_HEIGHT', message: `Screen '${screen.id}', frame '${el.id}': height must be greater than zero` });
          }
          break;
      }
    }

    const itemIdsOnScreen = new Set<string>();
    for (const item of screen.items) {
      if (itemIdsOnScreen.has(item.id)) {
        issues.push({ severity: 'ERROR', code: 'SCREEN_ITEM_DUPLICATE_ID', message: `Screen '${screen.id}': duplicate item id '${item.id}'` });
      }
      itemIdsOnScreen.add(item.id);

      if (item.symbol.trim().length === 0) {
        issues.push({ severity: 'ERROR', code: 'SCREEN_ITEM_EMPTY_SYMBOL', message: `Screen '${screen.id}', item '${item.id}': symbol must not be empty` });
      }

      // The same device on multiple screens, and a device on no screen at
      // all, are both correct - that is the point of this architecture.
      // Only an unknown device id is an error.
      if (item.device !== undefined && !knownDeviceIds.has(item.device)) {
        issues.push({ severity: 'ERROR', code: 'SCREEN_ITEM_UNKNOWN_DEVICE', message: `Screen '${screen.id}', item '${item.id}': device '${item.device}' does not exist in the device registry` });
      }
    }

    const seenConnIds = new Set<string>();
    for (const conn of screen.connections) {
      if (seenConnIds.has(conn.id)) {
        issues.push({ severity: 'ERROR', code: 'SCREEN_CONNECTION_DUPLICATE_ID', message: `Screen '${screen.id}': duplicate connection id '${conn.id}'` });
      }
      seenConnIds.add(conn.id);

      if (!itemIdsOnScreen.has(conn.fromItem)) {
        issues.push({ severity: 'ERROR', code: 'SCREEN_CONNECTION_DANGLING_FROM', message: `Screen '${screen.id}', connection '${conn.id}': fromItem '${conn.fromItem}' does not exist on this screen` });
      }
      if (!itemIdsOnScreen.has(conn.toItem)) {
        issues.push({ severity: 'ERROR', code: 'SCREEN_CONNECTION_DANGLING_TO', message: `Screen '${screen.id}', connection '${conn.id}': toItem '${conn.toItem}' does not exist on this screen` });
      }
      if (conn.fromItem === conn.toItem) {
        issues.push({ severity: 'ERROR', code: 'SCREEN_CONNECTION_SELF', message: `Screen '${screen.id}', connection '${conn.id}': fromItem and toItem must not be the same element` });
      }
    }

    const seenNavIds = new Set<string>();
    for (const nav of screen.navigation) {
      if (seenNavIds.has(nav.id)) {
        issues.push({ severity: 'ERROR', code: 'NAVIGATION_DUPLICATE_ID', message: `Screen '${screen.id}': duplicate navigation link id '${nav.id}'` });
      }
      seenNavIds.add(nav.id);

      if (nav.label.trim().length === 0) {
        issues.push({ severity: 'ERROR', code: 'NAVIGATION_EMPTY_LABEL', message: `Screen '${screen.id}', navigation link '${nav.id}': label must not be empty` });
      }
      if (!seenScreenIds.has(nav.targetScreen)) {
        issues.push({ severity: 'ERROR', code: 'NAVIGATION_UNKNOWN_TARGET', message: `Screen '${screen.id}', navigation link '${nav.id}': targetScreen '${nav.targetScreen}' does not exist` });
      } else if (nav.targetScreen === screen.id) {
        issues.push({ severity: 'ERROR', code: 'NAVIGATION_SELF_TARGET', message: `Screen '${screen.id}', navigation link '${nav.id}': targetScreen must not be this screen itself` });
      }
    }
  }

  const hasErrors = issues.some(i => i.severity === 'ERROR');
  return { valid: !hasErrors, issues };
}
