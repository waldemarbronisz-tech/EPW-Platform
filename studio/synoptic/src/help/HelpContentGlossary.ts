// feat/help-system commit 6 - the 'glossary-all' topic's own intro body.
// The actual term/definition list (HelpGlossary.ts) is rendered specially
// by HelpWindow.tsx, not as generic HelpBlocks - this is just the short
// framing text shown above that list, so the topic still has real
// content of its own like every other (mandatory tests 1/2).

import type { HelpContentMap } from './HelpContentRegistry';

export const HELP_CONTENT_GLOSSARY: HelpContentMap = {
  'glossary-all': {
    pl: [
      { kind: 'p', text: 'Ponizej sa zebrane najwazniejsze pojecia uzywane w tej pomocy, w porzadku alfabetycznym. Kazde haslo odsyla do rozdzialu, ktory omawia je w pelni - slownik jest skrotem, nie zastepstwem dla wlasciwej tresci.' },
      { kind: 'p', text: 'Strzalka przy definicji przenosi wprost do rozdzialu, ktory dane pojecie opisuje szczegolowo - kliknij ja, zeby zobaczyc pelny kontekst zamiast samej skroconej definicji.' },
    ],
    en: [
      { kind: 'p', text: 'Below are the most important terms used throughout this help, in alphabetical order. Every entry links to the chapter that covers it in full - the glossary is a shortcut, not a replacement for the actual content.' },
      { kind: 'p', text: 'The arrow next to a definition jumps straight to the chapter that covers that concept in depth - click it to see the full context instead of just the short definition.' },
    ],
  },
};
