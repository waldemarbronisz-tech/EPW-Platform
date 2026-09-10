// Same small Node ESM loader hook as shared/docs/ts_extension_resolver.mjs
// (branch docs/symbol-inventory, not yet merged as of this spike) -
// copied here rather than imported across branches so this spike stays
// self-contained on its own branch. Resolves this project's
// extensionless relative TS imports, which Node's own loader (unlike
// Vite/tsc) does not do on its own.
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const CANDIDATE_EXTENSIONS = ['.ts', '.tsx'];

export async function resolve(specifier, context, nextResolve) {
  const isRelative = specifier.startsWith('./') || specifier.startsWith('../');
  if (isRelative && !path.extname(specifier)) {
    const baseDir = path.dirname(fileURLToPath(context.parentURL));
    for (const ext of CANDIDATE_EXTENSIONS) {
      if (existsSync(path.join(baseDir, specifier + ext))) {
        return nextResolve(specifier + ext, context);
      }
    }
  }
  return nextResolve(specifier, context);
}
