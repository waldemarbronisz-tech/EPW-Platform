// Task "migracja adresacji", etap 4: the platform-wide proof.
//
// runtime and Logic Studio share one Python file (shared/addressing.py,
// loaded by both epw_os/core/addressing.py and
// logic_studio/core/addressing.py as thin by-path shims - see either
// shim's own module docstring) - agreement between those two is a
// tautology. Synoptic Editor is TypeScript, a different language
// runtime that cannot import that file at all, so parseChannelAddress
// here is a genuine, independently-maintained fourth implementation of
// the same grammar.
//
// shared/addressing_grammar_vectors.json is the one fixture every
// implementation is checked against - this file drives it against
// parseChannelAddress; the three Python copies of this same test
// (runtime/epw_os/tests, studio/logic/tests, studio/shell/tests) drive
// the identical list against shared/addressing.py. Neither side imports
// the other - agreement is proven by both independently matching the
// same ground truth.
//
// To see this test actually catch a divergence: temporarily revert the
// etap-3 fix in DeviceValidation.ts (`/^[1-9][0-9]*$/` back to
// `/^[0-9]+$/`) and re-run - the "ELA1.DI.05" case below fails
// immediately. Done once, by hand, while writing this test, then
// reverted - see the etap-3 report for the transcript.

import { describe, it, expect } from 'vitest';
import { parseChannelAddress } from '../project/DeviceValidation';

// CI fix: `node:fs`/`node:url`/`node:path` compile fine under vitest's own
// module resolution (that's why "Test" passed) but `tsc -b` (the "Build"
// step, a SEPARATE type-check with no Node globals in its own tsconfig -
// see interface-language-commit4.test.ts's own header comment for the
// exact same constraint) rejects them outright - a real, CI-breaking gap
// this file shipped with. Vite's own import.meta.glob (eager, ?raw) is
// the Node-free way every other test in this tree already reads a file
// from disk - src/tests -> src -> studio/synoptic -> studio -> repo root.
const vectorsFile = import.meta.glob('../../../../shared/addressing_grammar_vectors.json', {
  query: '?raw', import: 'default', eager: true,
}) as Record<string, string>;
const vectorsRaw = Object.values(vectorsFile)[0];
const vectors = JSON.parse(vectorsRaw) as {
  cases: Array<{ input: unknown; valid: boolean; card?: string; kind?: string; channel?: number }>;
};

describe('parseChannelAddress matches the shared cross-platform vector list', () => {
  it('has both valid and invalid cases (guards against a silently-empty fixture)', () => {
    expect(vectors.cases.some(c => c.valid)).toBe(true);
    expect(vectors.cases.some(c => !c.valid)).toBe(true);
  });

  for (const testCase of vectors.cases) {
    const label = JSON.stringify(testCase.input);
    it(`${label} -> ${testCase.valid ? 'valid' : 'rejected'}`, () => {
      const result = parseChannelAddress(testCase.input as string);
      if (testCase.valid) {
        expect(result).toEqual({ card: testCase.card, kind: testCase.kind, channel: testCase.channel });
      } else {
        expect(result).toBeNull();
      }
    });
  }
});
