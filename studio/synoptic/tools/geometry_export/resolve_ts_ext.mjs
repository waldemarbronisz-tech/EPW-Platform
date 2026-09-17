// Node module-resolution hook: lets `import ... from './SymbolRegistry'`
// (extension-less, the way the editor's own TypeScript sources import
// each other) resolve to the .ts/.tsx file when the exporter imports
// the registry directly under Node's built-in type stripping.
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const CANDIDATE_EXTENSIONS = ['.ts', '.tsx'];

export async function resolve(specifier, context, nextResolve) {
  const isRelative = specifier.startsWith('./') || specifier.startsWith('../');
  if (isRelative && !path.extname(specifier) && context.parentURL) {
    const baseDir = path.dirname(fileURLToPath(context.parentURL));
    for (const ext of CANDIDATE_EXTENSIONS) {
      if (existsSync(path.join(baseDir, specifier + ext))) {
        return nextResolve(specifier + ext, context);
      }
    }
  }
  return nextResolve(specifier, context);
}
