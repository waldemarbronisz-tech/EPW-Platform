// Human-readable identification for an object, for anything shown to
// the user (Messages panel entries, etc.) - never its raw id, which is
// a UUID and means nothing to a person reading the log.

import type { SynopticObject } from '../store';
import { getSymbolDefinition } from '../symbols/SymbolRegistry';

/**
 * designation when the user has set one (e.g. "-Q1"), otherwise the
 * symbol's own readable library label (e.g. "Load Switch") - never the
 * type identifier string (e.g. "scada.load_switch") and never the
 * object's id.
 */
export function describeObject(obj: SynopticObject | undefined | null): string {
  if (!obj) return 'unknown object';
  return obj.designation || getSymbolDefinition(obj.type)?.label || obj.type;
}
