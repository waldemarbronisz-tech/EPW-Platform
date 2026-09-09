// fix/inline-device-creation commit 2: the ONE place that decides
// whether a candidate location/card may be appended to the registry -
// shared, verbatim, by DeviceRegistriesDialog.tsx's own Dodaj/Zapisz
// rows and the two new mini "add location"/"add card" dialogs opened
// from within DeviceFormDialog.tsx (AddLocationDialog.tsx,
// AddCardDialog.tsx via ChannelAddressPicker.tsx). GRANICE requires one
// shared function for each, not a second copy of the rule anywhere in
// interface code - this file, not either dialog, is that one place.
// Both call sites still run through validateDeviceRegistry
// (DeviceValidation.ts) as the sole source of truth for format/
// uniqueness; this file only builds the candidate registry and reads
// back the issues that mention the new code/id, exactly as
// DeviceRegistriesDialog.tsx's own inline version already did before
// this commit pulled it out.
//
// Returns the full ValidationIssue, not just its message, so a caller
// that needs the CODE (mandatory test 6: a duplicate location code must
// be rejected with the exact same error code the Registries window
// itself would show) can read it back without a second, parallel
// lookup - both paths call this one function, so identical codes follow
// from construction, not convention.
import type { CardEntry, Device, LocationEntry } from './DeviceSchema';
import { validateDeviceRegistry, type ValidationIssue } from './DeviceValidation';

export type RegistryMutationOutcome =
  | { ok: true }
  | { ok: false; issue: ValidationIssue };

/** Every ValidationIssue whose message mentions this exact quoted code/id. */
export function issuesMentioning(issues: ValidationIssue[], quoted: string): ValidationIssue[] {
  const needle = `'${quoted}'`;
  return issues.filter(i => i.message.includes(needle));
}

/**
 * Checks whether `candidate` may be appended to `locations` - builds
 * the full registry (this candidate plus the other two lists
 * unchanged) and runs it through validateDeviceRegistry. Does NOT
 * mutate anything: on ok, the caller still commits via the store's own
 * addLocation action itself.
 */
export function checkAddLocation(
  candidate: LocationEntry,
  locations: LocationEntry[],
  cards: CardEntry[],
  devices: Device[]
): RegistryMutationOutcome {
  const result = validateDeviceRegistry({ locations: [...locations, candidate], cards, devices });
  const relevant = issuesMentioning(result.issues, candidate.code || '(puste)');
  return relevant.length > 0 ? { ok: false, issue: relevant[0] } : { ok: true };
}

/** Same pattern as checkAddLocation, for a card. */
export function checkAddCard(
  candidate: CardEntry,
  locations: LocationEntry[],
  cards: CardEntry[],
  devices: Device[]
): RegistryMutationOutcome {
  const result = validateDeviceRegistry({ locations, cards: [...cards, candidate], devices });
  const relevant = issuesMentioning(result.issues, candidate.id || '(puste)');
  return relevant.length > 0 ? { ok: false, issue: relevant[0] } : { ok: true };
}
