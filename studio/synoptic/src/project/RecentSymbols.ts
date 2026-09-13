// feat/library-recent-and-search: the symbols you actually keep reaching
// for, kept at the top of the library.
//
// The Logic editor has had this for a while (logic_studio/ui/panels/
// library.py - "Ostatnio uzywane", ten entries, most recent first) and
// this is deliberately the same rule rather than a second, subtly
// different one: the two editors sit in the same shell, and a library
// that behaves differently in each is a library you have to learn twice.
//
// PERSISTED, because a list that empties on restart is not the list that
// was asked for - you come back to a drawing tomorrow and carry on
// placing the same six symbols. It goes to localStorage, which is what
// the panel layout beside it already uses (App.tsx's autoSaveId), inside
// a try/catch: a browser with storage disabled must degrade to a
// session-only list, never fail to open the library.
//
// Pure list logic here; the store holds the live value.

/** How many to remember. Ten, the same as the Logic editor's own RECENT_MAX - long enough to cover a working session's vocabulary, short enough to stay scannable without its own scrollbar. */
export const RECENT_MAX = 10;

/** The heading, matching the Logic editor's own wording. */
export const RECENT_LABEL = 'Recently used';

const STORAGE_KEY = 'epw-synoptic/library-recent';

/**
 * `type` moved to the front, with any earlier occurrence removed and the
 * list trimmed.
 *
 * Re-using a symbol has to MOVE it rather than duplicate it, or the list
 * fills up with one symbol and nothing else - which is exactly the
 * symbol you least need help finding.
 */
export function recordRecent(recent: string[], type: string): string[] {
  if (!type) return recent;
  return [type, ...recent.filter(t => t !== type)].slice(0, RECENT_MAX);
}

/** The stored list, or an empty one. Never throws: a browser with storage blocked gets a session-only list rather than an editor that will not start. */
export function loadRecent(): string[] {
  try {
    const raw = globalThis.localStorage?.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((t): t is string => typeof t === 'string').slice(0, RECENT_MAX);
  } catch {
    return [];
  }
}

/** Writes the list back. Silent on failure, for the same reason loadRecent is. */
export function saveRecent(recent: string[]): void {
  try {
    globalThis.localStorage?.setItem(STORAGE_KEY, JSON.stringify(recent.slice(0, RECENT_MAX)));
  } catch {
    // Storage full, disabled, or a private window. The list still works
    // for this session; losing it at restart is not worth an error.
  }
}

/** The stroked l, which is a letter in its own right rather than an l with a mark, so NFD leaves it alone and it has to be folded by hand. Built from its code point so this file stays ASCII. */
const STROKED_L = String.fromCharCode(0x142);

/**
 * Whether a library entry matches what was typed.
 *
 * Matches the LABEL and the TYPE both, because people search for either:
 * "oprawa" is what it is called, "luminaire" is what it is. Case- and
 * accent-insensitive over the Polish letters the labels actually use, so
 * a query typed without diacritics still finds a label that has them - a
 * search that only works when you type them is a search most people
 * conclude is broken.
 */
export function matchesQuery(label: string, type: string, query: string): boolean {
  const needle = normalize(query);
  if (!needle) return true;
  return normalize(label).includes(needle) || normalize(type).includes(needle);
}

function normalize(value: string): string {
  return value
    // Trimmed here rather than at the call site: a query of nothing but
    // spaces is not a query, and leaving it untrimmed would filter out
    // every symbol the moment somebody hit the space bar.
    .trim()
    .toLowerCase()
    // Decompose the accented letters, then drop every combining mark -
    // the Unicode mark property instead of a hand-written a-with-ogonek
    // table that would sooner or later miss one.
    .normalize('NFD')
    .replace(/\p{M}/gu, '')
    .split(STROKED_L)
    .join('l');
}

/**
 * Whether any of several names - a symbol's Polish name, its English name,
 * its registry label - or its type matches what was typed. The library
 * search uses it so a query finds a symbol in either language, whichever
 * language the interface is in.
 */
export function matchesAnyName(names: string[], type: string, query: string): boolean {
  const needle = normalize(query);
  if (!needle) return true;
  return names.some(name => normalize(name).includes(needle)) || normalize(type).includes(needle);
}
