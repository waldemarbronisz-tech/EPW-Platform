// Node ESM loader hook used only by generate_symbol_inventory.mjs.
//
// The Synoptic Editor's TypeScript sources import relative modules with
// no file extension ("./registry/electrical", not "./registry/
// electrical.ts") - normal for a project built through Vite/tsc, which
// both resolve extensionless specifiers themselves. Node's own ESM
// loader does not - it requires an exact, existing specifier - so a
// plain `node --experimental-strip-types` import of SymbolRegistry.ts
// fails on its very first extensionless import.
//
// This hook does exactly one thing: if a relative specifier has no
// extension and a same-named ".ts"/".tsx" file exists next to the
// importer, resolve to that file instead. No dependency added - this
// is ~15 lines using only node:fs/node:path/node:url, registered via
// node:module's built-in `register()` API.
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
