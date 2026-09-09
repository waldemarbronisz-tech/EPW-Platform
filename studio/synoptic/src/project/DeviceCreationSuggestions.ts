// fix/inline-device-creation commit 3: the suggestion functions
// DeviceFormDialog.tsx's own "create or assign" mode calls once a
// location is picked - a NEW id suffix and a NEW designation, both
// typed AND selected so the very first keystroke overwrites them (the
// selecting itself happens in DeviceFormDialog.tsx, via a ref and
// .select() - this file only computes the values).
//
// Both suggestions work the same way: look at devices ALREADY in this
// location that are the same kind of thing as the one being created: if
// any exist, read back whatever letter-prefix convention they already
// use and continue it (mandatory test 13: KOT_KMG1 + KOT_KMG2 already
// exist -> KOT_KMG3, whatever "KMG" happens to stand for in this
// project - this function never needs to re-derive that abbreviation
// from the word "contactor" itself, only to notice it is already there
// twice and continue it). If none exist yet, mandatory test 14 only
// requires the suggested NUMBER to be 1 - the letter-prefix used in
// that case is this function's own reasonable fallback, not a value
// GRANICE fixes: id suffix falls back to the first letters of `kind`,
// designation falls back to a small IEC-reference-designation-style
// letter for the behavior (K for a switched/controlled device, B for a
// measured one - the same convention the task's own two examples,
// "-K1, -K2" and "-B1", already follow).
import type { Device, DeviceBehavior } from './DeviceSchema';
import { getDeviceLocationCode } from './DeviceRegistryQueries';

/** 'electrical.disconnect_switch' -> 'disconnect_switch' - the free-text `kind` a symbol of this type gets suggested when creationContext is active (DeviceFormDialog.tsx), and the key both suggestion functions below group existing devices by. */
export function deriveKindFromSymbolType(symbolType: string): string {
  const dot = symbolType.lastIndexOf('.');
  return dot >= 0 ? symbolType.slice(dot + 1) : symbolType;
}

function normalizeKind(kind: string): string {
  return kind.trim().toLowerCase();
}

/** Splits a suffix/designation-letters string like 'KMG12' or 'K3' into its leading letters and trailing number - null if it does not end in at least one digit. */
function splitLettersAndNumber(value: string): { letters: string; number: number } | null {
  const match = /^([A-Za-z]*)(\d+)$/.exec(value);
  if (!match) return null;
  return { letters: match[1], number: parseInt(match[2], 10) };
}

/** Among `values` (already-used suffixes or designation letters for devices of the SAME kind), the most common leading-letters prefix and the highest number already used under it - undefined if none of them parse as letters+digits. */
function dominantPrefixAndMax(values: string[]): { prefix: string; max: number } | undefined {
  const maxByPrefix = new Map<string, number>();
  for (const value of values) {
    const parsed = splitLettersAndNumber(value);
    if (!parsed) continue;
    maxByPrefix.set(parsed.letters, Math.max(maxByPrefix.get(parsed.letters) ?? 0, parsed.number));
  }
  if (maxByPrefix.size === 0) return undefined;
  // The prefix with the most existing devices wins (a location settled
  // on one convention almost always has only one anyway); a tie keeps
  // whichever was inserted first - Map preserves insertion order, and
  // values are walked in the same order `values` was given.
  let bestPrefix = '';
  let bestCount = -1;
  const countByPrefix = new Map<string, number>();
  for (const value of values) {
    const parsed = splitLettersAndNumber(value);
    if (!parsed) continue;
    const count = (countByPrefix.get(parsed.letters) ?? 0) + 1;
    countByPrefix.set(parsed.letters, count);
    if (count > bestCount) { bestCount = count; bestPrefix = parsed.letters; }
  }
  return { prefix: bestPrefix, max: maxByPrefix.get(bestPrefix)! };
}

/** First letters of each underscore/space-separated word in `kind`, uppercased, e.g. 'disconnect_switch' -> 'DS', 'contactor' -> 'CON' (a single word falls back to its first three letters, so a fresh kind never suggests a bare one-letter id). */
function fallbackLettersForKind(kind: string): string {
  const words = normalizeKind(kind).split(/[^a-z0-9]+/).filter(Boolean);
  if (words.length === 0) return 'DEV';
  if (words.length === 1) return words[0].slice(0, 3).toUpperCase();
  return words.map(w => w[0]).join('').toUpperCase();
}

const FALLBACK_DESIGNATION_LETTER: Record<DeviceBehavior, string> = {
  // Matches the task's own two examples verbatim: a switched
  // (controlled) device suggests -K (kontaktor/stycznik/wylacznik
  // convention), a measured one suggests -B (czujnik/przetwornik).
  // SIGNAL/MODULATED/SELECTOR are not part of Commit 3's own behavior
  // mapping (SymbolBehaviorMapping.ts) but still need SOME fallback if
  // the user picks one by hand after the suggestion.
  SWITCHED: 'K',
  SIGNAL: 'S',
  MEASURED: 'B',
  MODULATED: 'U',
  SELECTOR: 'S',
};

/**
 * Suggests the next free id SUFFIX (not the full id - DeviceFormDialog's
 * own `suffix` state already excludes the location code and its own
 * underscore) for a new device of `kind` in `locationCode`.
 */
export function suggestNextDeviceIdSuffix(locationCode: string, kind: string, devices: Device[]): string {
  const sameLocationSameKind = devices.filter(d =>
    getDeviceLocationCode(d.id) === locationCode && normalizeKind(d.kind) === normalizeKind(kind)
  );
  const suffixes = sameLocationSameKind.map(d => d.id.slice(locationCode.length + 1));
  const dominant = dominantPrefixAndMax(suffixes);
  if (dominant) return `${dominant.prefix}${dominant.max + 1}`;
  return `${fallbackLettersForKind(kind)}1`;
}

/**
 * Suggests the next free designation (with its leading '-') for a new
 * device of `behavior`/`kind` in `locationCode` - same "continue what is
 * already there, else fall back" shape as suggestNextDeviceIdSuffix.
 */
export function suggestNextDesignation(locationCode: string, behavior: DeviceBehavior, kind: string, devices: Device[]): string {
  const sameLocationSameKind = devices.filter(d =>
    getDeviceLocationCode(d.id) === locationCode && normalizeKind(d.kind) === normalizeKind(kind)
  );
  const letterSuffixes = sameLocationSameKind
    .map(d => d.designation)
    .filter(desig => desig.startsWith('-'))
    .map(desig => desig.slice(1));
  const dominant = dominantPrefixAndMax(letterSuffixes);
  if (dominant) return `-${dominant.prefix}${dominant.max + 1}`;
  return `-${FALLBACK_DESIGNATION_LETTER[behavior]}1`;
}
