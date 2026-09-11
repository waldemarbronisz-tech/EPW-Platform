# Geometry Export Spike: Can Path C's Premise Actually Be Built?

Reconnaissance prototype, not a renderer. Everything below is either
**ZMIERZONE** (measured - a script ran, a file exists, an image was
compared pixel-by-pixel) or **ZAŁOŻONE** (a judgment call, flagged as
such). No code from this spike is wired into `runtime/` or `studio/
synoptic/src/` - both stayed untouched except for reading.

Note on `shared/docs/SYMBOL_RENDERING_PATHS.md`: as of this spike, that
file exists only on branch `docs/symbol-inventory`, not on `main` - the
three prior reconnaissance branches have not actually been merged yet,
despite the task brief's premise ("na main po merge"). Not a blocker
for this task (nothing here needed to read it from disk - the content
is already known from writing it, and this spike only reads `studio/
synoptic/src/`, untouched by that merge status either way), but flagged
per this session's own rule to surface a wrong premise rather than
silently work around it.

---

## 1.1 - The four symbols

Exactly the four named in the task brief - all four exist under those
exact names, no substitution needed:

| # | Type | Difficulty class | Why this one |
|---|---|---|---|
| a | `electrical.circuit_breaker` | static, multi-state | 4 states (OPEN/CLOSED/TRIPPED/FAULT), pure `Line`+`Rect`, no animation, no terminals dependency in its own draw code |
| b | `electrical.indicator_lamp` | animated - blink | `setInterval`-driven blink, one `Circle` |
| c | `hvac.fan` | animated - rotation | `requestAnimationFrame`-driven rotation, nested `Group` + 4x `Arc` |
| d | `water.valve` | terminals + multiple states | 5 states, 2 terminals, pulls in a shared helper (`waterStub` from `site/BandedShading.tsx`) with its own further layers of composition - the deepest import graph of the four |

## 1.2 - The exporter

**Method chosen**: execute the REAL, unmodified `.tsx` component file
as a plain function - not through any renderer - by bundling it with
`esbuild` (JSX → `React.createElement` calls only, no type-checking)
against two ~30-line local stub modules (`spike/geometry_export/stubs/
react.js`, `stubs/react-konva.js`) instead of the real packages.
`createElement` in the stub just returns a plain `{type, props,
children}` object; `useState`/`useEffect` are stubbed to freeze every
component at its own declared **initial** pose (`angle=0`,
`blinkOn=true`) and never actually run an effect - so an animated
symbol's export captures its static base geometry, not one arbitrary
mid-animation frame. The resulting plain-object tree is walked
recursively and every primitive's absolute pixel values are divided by
the symbol's own `defaultWidth`/`defaultHeight` (from the real,
executed `SymbolRegistry.ts` - same technique as the prior symbol-
inventory task) to produce 0..1 fractions.

Animation is never traced from the timer code - `ANIMATION_DIRECTIVES`
in `extract.mjs` is a small, hand-authored table (2 entries, one per
animated symbol in this sample), each read directly from source:

- `electrical.indicator_lamp`: `{type: "blink", half_period_ms: 500}` -
  **ZMIERZONE**, `setInterval(..., 500)` is a literal, fixed constant.
- `hvac.fan`: `{type: "rotate", rate_deg_per_sec: 900, measured: false}` -
  **ZAŁOŻONE**. The source increments the angle by 15° per
  `requestAnimationFrame` callback, not per fixed time unit - real
  speed is coupled to the browser's display refresh rate (nominally
  ~60Hz, giving the 900°/s used here), which is not a constant recorded
  anywhere in source. This is the one number in the whole export that
  is an assumption, not a measurement, and the JSON says so explicitly
  (`"measured": false`) rather than presenting it as fact.

**Does this scale to the other 81 symbols, or does it only work for
these four?** Scales, with two known, small, enumerable gaps - see the
verdict's Q4 for the measurement behind that claim.

**Output**: `shared/docs/spike/geometry_sample.json` - all 4 symbols,
every one of their `allowedStates` (16 states total), full primitive
trees, normalized.

## 1.3 - The PySide6 prototype renderer

`spike/pyside_renderer/render_prototype.py` - reads the JSON above and
knows exactly six primitive kinds (`group`/`rect`/`circle`/`line`/
`arc`/`path`, plus `text`) and nothing else. Zero knowledge of "a
valve" or "a fan" anywhere in this file - the same drawing code handled
all four samples. An unrecognized primitive kind draws a visible
magenta `?kind` marker rather than silently vanishing - a real gap
would show up in the output image, not just in a log.

## 1.4 - The comparison (the actual evidence)

Two PNGs, same layout, same 4x upscale, same 16 (symbol, state) cells,
in `shared/docs/spike/`:

- **`editor_reference.png`** - NOT a screenshot of the running web app
  (no browser or dev server was started for this spike). It IS the
  real, unmodified component files, run through real `react` + real
  `react-konva` + real `konva`, rendered headless via `konva/canvas-
  backend` + `node-canvas` - the identical rendering engine and
  identical component code the editor itself uses, with react-konva's
  `<Stage>` wrapper (which needs a real DOM `<div>` via react-dom)
  bypassed by driving its exported reconciler (`KonvaRenderer`)
  directly against a manually-constructed `Konva.Stage`. This is the
  strongest "what the editor actually draws" reference obtainable
  without standing up a browser.
- **`pyside_prototype.png`** - the generic PySide6 renderer above,
  fed `geometry_sample.json`.

**What differs, found by direct pixel-region comparison, not by eye
alone:**

1. `electrical.circuit_breaker`'s FAULT overlay (a dashed red rect,
   `dash={[4,2]}` in source) rendered as a visually near-solid red
   border in the first prototype pass - Qt's default line cap
   (`SquareCap`) extends each dash by half the pen width at both ends,
   which merges adjacent dashes together when the gap is smaller than
   the pen width (exactly this case: `strokeWidth=5`, dash gap `2`).
   Canvas/Konva's default cap is `butt` (no extension). **Found,
   diagnosed, and fixed** (`pen.setCapStyle(Qt.PenCapStyle.FlatCap)`,
   one line) - re-rendered, now clearly dotted, matching the reference.
   This is the one difference this spike actually had to debug.
2. Everything else compared - all 4 states of the circuit breaker, all
   4 of the lamp, all 3 of the fan (including the frozen-baseline
   RUNNING pose matching in both images), all 5 of the valve (including
   the partially-off-canvas stem in OPEN/OPENING/CLOSING and the
   `waterStub` terminal bars) - is visually indistinguishable between
   the two images at the compared resolution.

**Verdict on the difference: cosmetic, not disqualifying.** It was a
generic canvas-vs-Qt default-style mismatch (line caps), not a
per-symbol geometry error, and the fix is a single line applied once
in the shared drawing code, not sixteen one-off patches.

## 1.5 - The verdict

### Q1: Mechanical, or manual per symbol? How long did each take?

Not tracked with a stopwatch (no fabricated minute counts below) - the
real, checkable signal is **how much new code each symbol required**,
which is zero for most of them:

- `electrical.circuit_breaker` (first symbol): required building the
  whole pipeline from scratch - the stub modules, the esbuild
  invocation, the tree walker's `group`/`rect`/`circle`/`line` cases.
  This cost is attributable to standing up the FRAMEWORK, not to this
  symbol being hard - it uses only `Group`/`Rect`/`Line`, the simplest
  three primitive kinds.
- `electrical.indicator_lamp`: **zero new code.** `Circle` + `Rect`
  were already handled from the first symbol. Ran on the first try.
- `hvac.fan`: required exactly one addition - an `arc` case (JSON
  normalizer + PySide6 drawer, ~15 lines each) for Konva's `Arc`
  primitive, plus working out the Canvas-vs-Qt angle-direction sign
  flip (clockwise vs counterclockwise from 3 o'clock). Once added, the
  fan extracted and rendered correctly - the addition was for the
  PRIMITIVE KIND, not for "the fan" specifically.
- `water.valve`: required one more addition - a `path` case (~20 lines:
  a small `M`/`L`/`Z` tokenizer to normalize coordinates embedded
  inside an SVG path string, since those aren't separate x/y props).
  Also transitively pulled in `site/BandedShading.tsx`'s own helper
  functions (`waterStub`/`objectPipeSegment`/`waterFlange`) - these
  required zero special handling at all; esbuild bundled them
  automatically and they executed as plain functions like everything
  else.

**Conclusion: per-symbol effort was driven entirely by which
PRIMITIVE KINDS a symbol happens to use, not by anything specific to
the symbol itself.** A symbol using only primitive kinds already
supported costs nothing extra (confirmed directly: the lamp).

### Q2: Anything NOT expressible as primitives?

Two things, both already anticipated by this task's own framing, plus
one found only by checking beyond the 4 samples:

- **Animation itself** - by definition, a rotating/blinking pose is not
  a static shape. This is not a new finding (the task brief says so
  explicitly, "Animacja NIE jest geometrią") - it is confirmed exactly
  as expected, handled by the directive table instead.
- **Live wire-net connectivity** (the `terminalNetState` input) -
  `water.valve` is one of the 23 symbols identified in the prior
  rendering-paths report as depending on it. This export passed
  `terminalNetState: undefined`, so every extracted state shows the
  krociec terminal stubs in their default/INACTIVE appearance only -
  the ACTIVE-net colored variant is never captured by this pipeline at
  all, confirmed concretely in this sample (not just asserted from the
  earlier report). Out of scope here per this task's own GRANICE, but
  worth restating with a real example in hand rather than only in the
  abstract.
- **`globalCompositeOperation`** (a canvas compositing-mode property,
  used in `water/PipeElbowSymbol.tsx` and `water/TeeSymbol.tsx` - found
  by checking the wider library, not present in any of the 4 samples)
  is not in this exporter's style schema (`fill`/`stroke`/`strokeWidth`/
  `dash`/`opacity`/`listening` only). A real gap, small and enumerable,
  not fatal - the same "extend the shared schema once" shape as Arc/Path.

### Q3: Were the 3 predicted animation directives enough?

Only 2 of the 3 were exercised by this 4-symbol sample (blink,
rotate) - the third (dash-offset march, used by `electrical.ac_wire`/
`busbar`/`cable`/`three_phase_line`, `water.pipe`) was **not tested in
this spike** at all, since none of the four chosen symbols use it.
**ZMIERZONE**: 2/3 sufficed for the symbols that needed them, with zero
struggle. **ZAŁOŻONE, not verified here**: the third likely fits the
same directive shape (one fixed parameter - a scroll rate - read
directly from its own `requestAnimationFrame` increment, same pattern
as rotation) - but this is an inference from reading that code in the
prior task, not something this spike actually built and compared.

### Q4: Extrapolation to all 85 - how many, and on what basis?

**Measured basis, not a guess**: grepped every Konva JSX tag across all
87 component files in the library (not just the 4 samples). Exactly
**9 distinct primitive kinds** are used anywhere in the whole library:

| Primitive | Uses across the library | Handled by this spike? |
|---|---|---|
| Rect | 149 | Yes |
| Group | 113 | Yes |
| Line | 105 | Yes |
| Path | 53 | Yes |
| Circle | 49 | Yes |
| Text | 41 | Yes |
| Arc | 7 | Yes |
| Ellipse | 2 | **No** |
| Wedge | 1 | **No** |

**7 of 9 kinds, covering 517 of 520 total tag occurrences (99.4%),
are already implemented and validated by this spike against real
symbols.** `Ellipse` (a `Circle` with independent x/y radii) and
`Wedge` (an `Arc` with `innerRadius` fixed at 0) are both trivial,
bounded extensions of primitives already working - not new kinds of
problem, and used a combined 3 times in the entire library.

**Answer: on this basis, all 85 symbols' STATIC geometry should extract
and render through this exact pipeline with no per-symbol manual
intervention** - the demonstrated pattern (new code needed only per
NEW PRIMITIVE KIND encountered, never per symbol) covers 99.4% of all
tag usage already, and the remaining 0.6% is two small, well-understood
additions, not 81 unknowns. Two caveats attach to that "85," both
already known and neither a surprise:

- The 23 net-connectivity-dependent symbols would each extract and
  render their BASE geometry correctly, but without the live-net color
  variant (Q2) - a real, separate, un-started body of work
  (`NetResolver.ts`'s 328-line graph algorithm), not a gap in the
  export mechanism itself.
- `globalCompositeOperation` (2 files) and any other as-yet-unchecked
  Konva prop this spike's style schema doesn't carry would need the
  schema extended once, the same shape as every other gap found here.

**This spike does not show Path C failing.** It shows a mechanical
process that worked on the first attempt for 1 of 4 symbols, needed
one bounded addition each for the other 2 "new primitive kind" cases,
needed zero manual work for the remaining 1, and - checked against the
whole library, not just the sample - already covers 99.4% of what the
other 81 symbols would need. The one real, load-bearing gap this spike
confirms (not just repeats from the prior report) is net-connectivity,
and that was already known and explicitly out of scope here.
