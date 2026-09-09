// feat/site-objects-2d: shared state-narrowing helper for every TEREN
// symbol - SymbolRenderer.tsx only ever hands a plain, unvalidated
// string (obj.editor?.preview_state ?? a device-bound live value,
// eventually), same convention already established by
// scada/ScadaSymbolAdapters.tsx's own private resolveState. Shared
// here once (rather than copied into all 16 site components) since
// every one of them needs the exact same narrow-or-fall-back logic.
export function resolveSiteState<T extends string>(state: string, allowed: readonly T[], fallback: T): T {
  return (allowed as readonly string[]).includes(state) ? (state as T) : fallback;
}
