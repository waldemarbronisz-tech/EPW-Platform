// EPW SCADA visual theme - retro-industrial HMI style (Wonderware/iFIX
// era: flat fills, black outlines, color carries meaning and nothing
// else, conductors thicker than the symbols riding on them, strictly
// orthogonal routing).
//
// No other file may define these colors or these thicknesses on its own -
// every scada/ symbol imports them from here. A symbol may still use its
// own literal numbers for dimensions and outline widths the task gave it
// explicitly (e.g. the busbar's 3px outline, the label frame's 4px
// outline) - what must never be hand-written elsewhere is a PALETTE
// COLOR: every color a symbol paints with comes from this file.

// ---- Palette (exact values) ----

export const COLOR_CANVAS_BACKGROUND = '#00CFCF'; // tlo plotna
export const COLOR_OUTLINE = '#000000';           // kontur
export const COLOR_TEXT = COLOR_OUTLINE;          // tekst - same black as the outline
export const COLOR_PANEL = '#C6C6C6';             // panel
export const COLOR_BEVEL_LIGHT = '#F2F2F2';       // fazowanie jasne
export const COLOR_BEVEL_DARK = '#585858';        // fazowanie ciemne
export const COLOR_VALUE_FIELD = '#F2F2F2';       // pole wartosci
export const COLOR_ENERGIZED = '#E01000';         // pod napieciem
export const COLOR_DE_ENERGIZED = '#909090';      // bez napiecia
export const COLOR_RUN = '#00A800';               // stan zalaczony
export const COLOR_ALARM = '#D80000';             // stan alarmowy
export const COLOR_LAMP_LIT = '#FFE800';          // lampa swiecaca
export const COLOR_WATER = '#2848D8';             // woda aktywna
// feat/water-management commit 2: water conductor color now depends on
// net state too, the same ACTIVE/INACTIVE split every other medium
// already had - previously water ignored state entirely and always
// read as COLOR_WATER. Named INACTIVE (not e.g. COLOR_WATER_DEAD) to
// match VENTILATION_ACTIVE/VENTILATION_INACTIVE's own naming below.
export const COLOR_WATER_INACTIVE = '#C0C0C0';    // woda nieaktywna (jasnoszary)
export const COLOR_WHITE = '#FFFFFF';             // biel

// Ventilation (third medium, feat/media-and-proportions part B): gold
// reads clearly against both power's red and water's blue, and against
// the cyan canvas background - ACTIVE is a duct actually moving air,
// INACTIVE is a stopped/idle one, the same LIVE/DEAD split every other
// medium's conductor color already makes.
export const VENTILATION_ACTIVE = '#C89000';      // wentylacja aktywna
export const VENTILATION_INACTIVE = '#8A7A50';    // wentylacja nieaktywna

// feat/water-management commit 3: light/dark companions for every
// conductor color, for the new four-pass Houston-style pipe rendering's
// own highlight/shadow passes (ConnectionLine.tsx). Electrical and
// water sourced directly from docs/EPW_gospodarka_wodna_referencja.py's
// own palette - RD/DG/BL/G there each match an existing conductor color
// almost exactly at the BASE tone (RD #E00000 vs COLOR_ENERGIZED
// #E01000; DG #909090 = COLOR_DE_ENERGIZED exactly; BL #2848D8 =
// COLOR_WATER exactly; G #C0C0C0 = COLOR_WATER_INACTIVE exactly, added
// in commit 2) - confirmed by direct comparison, not assumed - so their
// own light/dark tones are reused here as-is rather than invented.
// Ventilation has no counterpart in that reference at all (a
// water-domain file, never mentioning the third medium) - its own pair
// below is extrapolated using the same relative lighten/darken ratio
// every other triad there consistently uses, not sourced from it.
export const COLOR_ENERGIZED_LIGHT = '#FF7070';
export const COLOR_ENERGIZED_DARK = '#900000';
export const COLOR_DE_ENERGIZED_LIGHT = '#C8C8C8';
export const COLOR_DE_ENERGIZED_DARK = '#585858';
export const COLOR_WATER_LIGHT = '#5878FF';
export const COLOR_WATER_DARK = '#182C90';
export const COLOR_WATER_INACTIVE_LIGHT = '#F0F0F0';
export const COLOR_WATER_INACTIVE_DARK = '#808080';
export const VENTILATION_ACTIVE_LIGHT = '#FFC850';
export const VENTILATION_ACTIVE_DARK = '#906000';
export const VENTILATION_INACTIVE_LIGHT = '#B8A878';
export const VENTILATION_INACTIVE_DARK = '#5C5030';

// ---- Geometry ----

// Conductor/symbol proportions derived directly from the grid (feat/
// media-and-proportions, part A): a conductor riding half a grid cell
// reads as a wire under an apparatus symbol, not the other way round -
// the earlier values (11/6/22) made a breaker on a power run get lost
// inside its own cable, confirmed by eye in the running app.
export const CONDUCTOR_WIDTH = 8;    // grubosc rdzenia przewodu - pol oczka siatki
// feat/water-management commit 3: was 4, now core+5 - docs/EPW_
// gospodarka_wodna_referencja.py's own pipe_seg draws its outline pass
// at stroke-width={w+5} (w being its own core parameter) - exactly this
// same relationship, applied to CONDUCTOR_WIDTH as that reference's own
// w. LoadSwitchSymbol.tsx/MotorSymbol.tsx/SocketSymbol.tsx each embed
// their own short conductor stub using this same constant, so they
// stay visually matched to the wire's own new outline automatically -
// no separate change needed in any of them.
export const CONDUCTOR_OUTLINE = 5;  // laczna grubosc konturu
// pipe_seg's own third pass (the light/highlight stroke): width 3.5,
// offset translate(-1,-3.2) - taken directly, unscaled (a cosmetic
// accent stroke, not grid-derived the way CONDUCTOR_WIDTH itself is).
export const CONDUCTOR_HIGHLIGHT_WIDTH = 3.5;
export const CONDUCTOR_HIGHLIGHT_OFFSET_X = -1;
export const CONDUCTOR_HIGHLIGHT_OFFSET_Y = -3.2;
// The reference's own header comment (and this task's own commit 3
// text) both promise FOUR passes - outline, fill, shadow, highlight -
// but its own pipe_seg function only actually draws three: no shadow
// line at all, confirmed by reading that function directly, not
// assumed. The values below are this pass's own deliberate, documented
// completion of that gap: the same width as the highlight (this task's
// own prose calls both "waski"/"waskie" - narrow - without
// distinguishing them), the offset exactly MIRRORED (down-right instead
// of up-left), and an opacity this task's own prose asks for
// ("polprzezroczysty") but never gives a number for either - 0.45
// reuses the same order of magnitude BandedShading.tsx's own glow()
// primitive already established for a soft overlay in this codebase
// (site-objects-2d), rather than inventing an unrelated number.
export const CONDUCTOR_SHADOW_WIDTH = 3.5;
export const CONDUCTOR_SHADOW_OFFSET_X = 1;
export const CONDUCTOR_SHADOW_OFFSET_Y = 3.2;
export const CONDUCTOR_SHADOW_OPACITY = 0.45;
export const SYMBOL_STROKE = 5;      // grubosc kreski wewnatrz symbolu
export const OUTLINE_WIDTH = 5;      // kontur ksztaltow wypelnionych (default; a
                                      // symbol may specify its own different
                                      // outline width when the task's spec for
                                      // that symbol gives one explicitly)
export const BUSBAR_HEIGHT = 16;     // wysokosc szyny zbiorczej - dokladnie jedno oczko
export const GRID_SIZE = 16;

// ---- Wire terminal hover/reach (fix/wiring-and-library-groups commit 1) ---
// usterka 1: a terminal dot sits ON a symbol's own edge (getTerminalOffsetForSide),
// so it visibly pokes half outside whatever the symbol actually draws there -
// hovering TOWARD the dot used to leave the Group's own (pixel-tight, per-
// shape) Konva hit area before the cursor ever reached it, hiding the very
// thing the user was chasing. TERMINAL_HOVER_MARGIN pads an invisible hit
// rect (ObjectNode.tsx) well past every terminal in every direction - "co
// najmniej promieniowi kropki razy trzy" (this task's own spec), taken
// directly rather than rounded to a different number.
export const TERMINAL_RADIUS = 6;                          // normal terminal dot (unchanged from before this fix)
export const TERMINAL_RADIUS_HIGHLIGHTED = 9;               // the one the cursor/magnetism would actually hit
export const TERMINAL_HOVER_MARGIN = TERMINAL_RADIUS * 3;   // padding around a symbol's own bbox that keeps its terminals reachable
export const TERMINAL_HIGHLIGHT_COLOR = COLOR_LAMP_LIT;     // reused, not a new literal - high-contrast against the normal COLOR_WATER fill
export const WIRE_NEARBY_TERMINAL_RADIUS = GRID_SIZE * 4;   // while drawing: terminals within this world distance stay visible without individual hover ("co najmniej cztery oczka")
export const WIRE_TERMINAL_SNAP_DISTANCE = GRID_SIZE / 2;   // magnetism: a wire endpoint snaps to a terminal closer than this ("polowa oczka siatki")

// ---- Wire collision / obstacle-avoidance routing (feat/wire-routing-
// around-obstacles commit 1/2) ------------------------------------------
// An obstacle's own rectangle is shrunk by this margin on every side
// before a wire segment is tested against it - a wire running right
// along an apparatus's own edge must not read as passing "through" it.
// Exactly this task's own spec: "margines rowny polowie oczka siatki".
export const WIRE_OBSTACLE_MARGIN = GRID_SIZE / 2;
// The colliding-segment overlay drawn on top of a wire that crosses an
// obstacle - dashed, in the theme's own alarm color (COLOR_ALARM above),
// wider than the wire's own core so it reads as an added marking, never
// a replacement for the wire's real state color.
export const WIRE_COLLISION_MARK_WIDTH = CONDUCTOR_WIDTH + 6;
export const WIRE_COLLISION_MARK_DASH: [number, number] = [8, 6];
// Router search cap (commit 2): a bound on how many grid cells the
// obstacle-avoidance search will expand before giving up and returning
// the direct point-to-point route instead - see WireRouter.ts's own
// header for why this exact number.
export const WIRE_ROUTER_STEP_LIMIT = 4000;

// feat/appearance-selection-frames commit 1: the indicator diode was
// drawn far too large relative to the row text beside it (confirmed by
// eye: a ten-row signal panel reads as a column of huge circles with
// the label an afterthought). These replace the two literal radii
// (8/12) IndicatorDiodeSymbol.tsx used to hold locally - moved here so
// every other place a diode radius might be needed reads the same
// single source, not a coincidentally-equal copy.
export const DIODE_RADIUS_SMALL = 5;  // przy aparatach na schemacie
export const DIODE_RADIUS_LARGE = 7;  // w panelach sygnalizacyjnych i stanu

// fix/handles-insert-mode-diodes commit 3: a lit (ON/ALARM/QUALITY)
// diode read as dark, matte, "painted" rather than actually glowing -
// confirmed by eye in the running app. These are the diode's OWN
// colors, deliberately separate from the state colors every other
// symbol paints with (COLOR_RUN/COLOR_ALARM/COLOR_LAMP_LIT) per this
// fix's own explicit spec, so the diode's own look can be tuned
// (brightness, the lit-core highlight below) without changing what
// every OTHER symbol's run/alarm/quality color means. The *_CORE
// colors are a brighter, smaller inner circle drawn only for a LIT
// state (IndicatorDiodeSymbol.tsx) - their own absence for OFF is
// what makes OFF read as "not lit", not a color choice of its own.
export const DIODE_ON = '#00E838';
export const DIODE_ON_CORE = '#A0FFB0';
export const DIODE_OFF = '#3C4048';
export const DIODE_ALARM = '#FF2020';
export const DIODE_ALARM_CORE = '#FFA0A0';
export const DIODE_QUALITY = '#FFD000';
export const DIODE_QUALITY_CORE = '#FFF0A0';

// ---- Typography ----
// One narrow sans-serif for everything that is a LABEL (row
// descriptions, object labels, titles) and one fixed-width face for
// everything that is a VALUE (a number, with or without a unit) - the
// same "flat, technical, nothing decorative" spirit the color palette
// above already commits to. Narrow is deliberate: a retro-industrial
// SCADA HMI's text reads denser and more technical than a default
// Arial ever does. Every component that draws text on the canvas, or
// in the surrounding HTML chrome, reads its font from here - never a
// hand-picked family or pixel size of its own (this file's own header
// comment already makes this rule for colors; it now also covers
// fonts).
export const FONT_UI = 'Tahoma, Verdana, "DejaVu Sans", sans-serif';
export const FONT_VALUE = 'Consolas, "DejaVu Sans Mono", monospace';
export const FONT_SIZE_BASE = 13;   // opisy wierszy, etykiety, teksty na plotnie
export const FONT_SIZE_SMALL = 11;  // druga linia etykiety, opisy pomocnicze
export const FONT_SIZE_TITLE = 14;  // tytuly miernika, panelu, ramki

// ---- HTML form chrome geometry --------------------------------------------
// fix/device-form-polish commit 1: the location-code <select> in
// DeviceFormDialog.tsx's own Id field used to render at a few pixels
// wide - a global CSS rule (index.css's own ".property-row select")
// gives every select/input in a property row flex:1/min-width:0, so
// with three other flex siblings in that same row (the + button, the
// literal "_" separator, the suffix input) it collapsed to almost
// nothing, its selected code entirely unreadable. Its own width is now
// computed from the registry's actual content (utils/CodePickerWidth.ts)
// instead, clamped between these two - GRANICE's own rule for this fix
// is explicit that no width may be a literal in the component itself.
export const LOCATION_PICKER_MIN_WIDTH = 96;   // never narrower, even for a one-character code
export const LOCATION_PICKER_MAX_WIDTH = 160;  // never wider, even for a very long code
export const SELECT_ARROW_ALLOWANCE = 24;      // room for the native dropdown arrow beside the text

// feat/site-objects-2d: docs/EPW_rysunki_referencja.py's own canvas is
// 160x120 (its W,H) - describing the reference DRAWING's own
// proportions, not literally the symbol's declared size in the
// library. terminal-centering.test.ts's own pre-existing invariant
// (feat/editing-and-signal-panel commit 1) requires every visible
// symbol's defaultWidth/defaultHeight to be an EVEN GRID_SIZE multiple
// (32, 64, 96, 128...), so a terminal's own edge-midpoint always lands
// on a grid node - 120 fails that (120/32 = 3.75), 160 alone would not
// have failed, but every one of these 16 objects needs a real terminal
// on at least one edge whose OTHER dimension is 120. Found live, this
// exact conflict was raised and resolved with the user: every site
// object's own DECLARED size is 128x96 - the identical 4:3 ratio as
// 160x120 (128/96 = 160/120), so nothing about the reference's own
// proportions is distorted - reached by drawing every shape at the
// reference's own literal 160x120 coordinates, then wrapping that
// whole drawing in one outer Group scaled by exactly this factor (the
// same scaleX/scaleY mechanism this app's own resize-by-handle already
// uses for every other symbol) rather than recalculating any
// coordinate by hand.
export const SITE_CANVAS_SCALE = 0.8; // 128/160 = 96/120

// ---- Site objects (feat/site-objects-2d) - banded shading -----------------
// A retro-industrial 90s SCADA HMI look, extended (not replaced - see this
// file's own header) to flat 2D site objects: buildings, gates, lighting,
// tanks... Every shape gets three tones - a lighter BAND along its own top
// (or left) edge, its own base fill everywhere else, a darker band along
// its own bottom (or right) edge - hard-edged, never a gradient, never
// blurred, never translucent in the shape itself (glow, below, is the one
// deliberate exception - a genuine light source, not shape shading). A
// round shape gets a light ARC upper-left and a shadow arc lower-right
// instead of straight bands. Every shape keeps the same solid black
// outline every other SCADA symbol already uses.
//
// Names and exact values below are taken VERBATIM from
// docs/EPW_rysunki_referencja.py's own header section (its sh() calls -
// base/light/dark, renamed here to base/light/dark for clarity, same
// order) - this file is the single, permanent home for them; the Python
// file itself is a geometry/color REFERENCE only, never executed, never
// imported by anything in src/.
export interface SiteShadeTriad {
  readonly base: string;
  readonly light: string;
  readonly dark: string;
}
export const SITE_GREY: SiteShadeTriad  = { base: '#C0C0C0', light: '#F0F0F0', dark: '#808080' };
export const SITE_DGREY: SiteShadeTriad = { base: '#909090', light: '#C8C8C8', dark: '#585858' };
export const SITE_GREEN: SiteShadeTriad = { base: '#00B800', light: '#50E850', dark: '#007000' };
export const SITE_RED: SiteShadeTriad   = { base: '#E00000', light: '#FF7070', dark: '#900000' };
export const SITE_BLUE: SiteShadeTriad  = { base: '#2848D8', light: '#6080FF', dark: '#182C90' };
export const SITE_TAN: SiteShadeTriad   = { base: '#C8A870', light: '#E8D0A0', dark: '#907040' };
export const SITE_YELL: SiteShadeTriad  = { base: '#FFD800', light: '#FFF080', dark: '#B08800' };
export const SITE_DARK: SiteShadeTriad  = { base: '#585C64', light: '#8C9098', dark: '#303438' };
export const SITE_CONC: SiteShadeTriad  = { base: '#D0D0C8', light: '#F0F0E8', dark: '#9C9C94' };
export const SITE_GRASS: SiteShadeTriad = { base: '#3C9430', light: '#68C050', dark: '#28641C' };
export const SITE_BRICK: SiteShadeTriad = { base: '#B45838', light: '#E08860', dark: '#7C3820' };

// Band/outline thicknesses (px) - every distinct value
// docs/EPW_rysunki_referencja.py's own rect/vrect/circ calls use,
// catalogued from that file directly (grep -oE "band=|ow=" across it) so
// every site object component below can reach for the exact one it needs
// instead of writing a literal of its own. The unsuffixed pair is each
// primitive's own DEFAULT (matching the reference's own rect(...,band=4,
// ow=2.5) default parameters).
export const SITE_BAND_WIDTH = 4;              // default shading band
export const SITE_BAND_WIDTH_NARROW = 3;       // window/door frames, posts, terminal rows...
export const SITE_BAND_WIDTH_NARROWEST = 2;    // zlacze's own terminal block rows
export const SITE_BAND_WIDTH_WIDE = 6;         // grass/road surface texture
export const SITE_OUTLINE_WIDTH = 2.5;         // default kontur
export const SITE_OUTLINE_WIDTH_MEDIUM = 2;    // most circ() calls, several rect() overrides
export const SITE_OUTLINE_WIDTH_THIN = 1.8;    // oczyszczalnia's own inner circles
export const SITE_OUTLINE_WIDTH_THINNEST = 1.5; // zlacze's own terminal rows
export const SITE_TEXTURE_LINE_WIDTH = 1.6;    // magazyn's cladding lines, brama's gate-leaf slats
export const SITE_CROSSBAR_WIDTH = 7;          // slup's own lamp-post crossbar
export const SITE_CONNECTOR_WIDTH = 6;         // halogen's own connecting bar

// Bespoke triads/colors docs/EPW_rysunki_referencja.py defines INLINE
// (its own sh(...) calls outside the header section, or a single raw
// hex) rather than from the eleven named sets above - each used by
// exactly one object, added here (not the object's own component file)
// for the same reason the eleven above are: GRANICE's "every color
// from ScadaTheme, never hand-written in the component" applies to
// these exactly as much as to the named ones.
export const SITE_BRICK_DIM: SiteShadeTriad = { base: '#8C6050', light: '#B08878', dark: '#5C3828' }; // dom's own roof, WYLACZONY
export const SITE_WOOD: SiteShadeTriad = { base: '#8C6038', light: '#B08050', dark: '#5C3820' };      // dom's own door
export const SITE_CHIMNEY: SiteShadeTriad = { base: '#909090', light: '#C0C0C0', dark: '#585858' };   // dom's own chimney
export const SITE_METAL_TEXTURE = '#707070';   // magazyn's own corrugated-wall cladding lines
export const SITE_PANEL_TEXTURE = '#404448';   // magazyn's own rolling-door panel lines
export const SITE_WATER_DIM: SiteShadeTriad = { base: '#5C6470', light: '#8C94A0', dark: '#3C4450' }; // oczyszczalnia's own chamber, WYLACZONY
export const SITE_RIB_LINE = '#606060';        // studzienka's own radial ribbing
export const SITE_CROSSBAR_HIGHLIGHT = '#B0B0B0'; // slup's own crossbar highlight line
export const SITE_RED_DIM: SiteShadeTriad = { base: '#8C3838', light: '#B06060', dark: '#5C2020' }; // kogut's own dome, WYLACZONY
export const SITE_RED_DIM_HIGHLIGHT = '#A05858'; // kogut's own highlight arc, WYLACZONY
export const SITE_ALARM_GLOW = '#FF3030';      // kogut's own glow tint (distinct from SITE_RED)
export const SITE_ALARM_RAY = '#FF4040';       // kogut's own radiating alarm rays, ZALACZONY
export const SITE_ALARM_RAY_WIDTH = 5;         // kogut's own radiating alarm rays, ZALACZONY
export const SITE_HORN_LIT: SiteShadeTriad = { base: '#D8D8D0', light: '#F8F8F0', dark: '#A0A098' }; // tuba's own horn, ZALACZONY
export const SITE_WATER_SPRAY = '#60A0FF';     // slupek_podl's own watering arcs

// Commit 4 (trawa/droga - the two SURFACE objects): trawa's own
// WYLACZONY (yellowed) grass triad - docs/EPW_rysunki_referencja.py's
// own trawa(on): `g = GRASS if on else sh('#8C9440','#B0B860','#5C6428')`.
// droga has no bespoke color of its own at all - it reuses SITE_CONC
// (Commit 1) for its slab surface and COLOR_WHITE (pre-existing) for
// its lane-marking dashes, plus one new joint-line color below.
export const SITE_GRASS_DIM: SiteShadeTriad = { base: '#8C9440', light: '#B0B860', dark: '#5C6428' }; // trawa's own texture+fill, WYLACZONY
export const SITE_ROAD_JOINT = '#A0A098';      // droga's own expansion-joint lines and center line

// feat/water-management commit 4 - docs/EPW_gospodarka_wodna_
// referencja.py's own palette (G/DG/BL/CO/GR/RD/YE/DK triads) matches
// the SITE_* triads above almost exactly at every base tone (confirmed
// by direct comparison: G=SITE_GREY, DG=SITE_DGREY, BL=SITE_BLUE (base/
// dark exact, light off by one hex digit - not worth a second, near-
// duplicate triad), CO=SITE_CONC, GR=SITE_GREEN, RD=SITE_RED,
// YE=SITE_YELL, DK=SITE_DARK) - reused directly below, not redefined.
// Only the handful of colors genuinely NEW to this reference (its own
// `led()`/`val()` primitives, and the lever/pipe proportions its own
// valve functions use) get new names here.
export const SITE_LED_OFF = '#3C4048';         // led(): dioda wylaczona
export const SITE_LED_ON_GREEN = '#00E838';    // led(): domyslny kolor zalaczony (zawor3 A/B, hydrofor)
export const SITE_LED_ON_RED = '#E02020';      // led(): zawor3sel's own Z (zamkniety) position
export const SITE_LED_HIGHLIGHT = '#C0FFC8';   // led(): mala poswiata na zalaczonej diodzie
export const SITE_LEVER_WIDTH = 6;             // zawor3/zawor3sel's own lever handle bar
export const SITE_LEVER_ARROW_WIDTH = 3.5;     // zawor3/zawor3sel's own lever arrowhead
// pipe_seg's own default core width (w=13) for a water OBJECT's own
// internal pipe stub - distinct from CONDUCTOR_WIDTH (8), which is the
// MAIN CANVAS wire's own core: an object's internal geometry is drawn
// at this reference's own literal 128x96 coordinates, a different
// scale entirely from the schematic canvas proper.
export const SITE_OBJECT_PIPE_WIDTH = 13;
export const SITE_TANK_WINDOW_BG = '#F4F4EC'; // tank2's own external level window background

// feat/water-management commit 5.
export const SITE_LCD_BACKGROUND = '#101418';  // przeplyw2/wodomierz2's own digital readout background
export const SITE_GAUGE_NEEDLE = '#C01818';    // presostat's own manometer needle
export const SITE_LED_ON_BLUE = '#3898FF';     // czujnik_deszczu's own led() color override
export const SITE_SPRAY_BLUE = '#5898FF';      // zraszacz's own water arcs (distinct from SITE_WATER_SPRAY - a different reference file's own literal value)

// fix/hydraulic-connections commit 5: docs/EPW_kolnierze_referencja.py's
// own hydraulic-connection standard - a stub (krociec) plus a flange
// (kolnierz) at EVERY water-medium object's own terminal. PIPE_W itself
// is not repeated here - it is SITE_OBJECT_PIPE_WIDTH above already,
// the exact same literal value (13) this reference's own PIPE_W is.
export const SITE_STUB_LENGTH = 14;                          // STUB - typical krociec length from an aparat's own body to its flange
export const SITE_FLANGE_THICKNESS = 6;                       // FL_W - the flange's own thickness along the pipe's axis
export const SITE_FLANGE_SPAN = SITE_OBJECT_PIPE_WIDTH + 11;  // FL_H = PIPE_W+11 - the flange's own span across the pipe

// ---- Bridge into CSS -----------------------------------------------------
// CSS cannot import a TypeScript module, so the interface chrome (panels,
// toolbar, property fields) reads these values through CSS custom
// properties instead of a second, hand-copied set of hex literals. This
// function is the ONLY place that writes them, and it must be called
// exactly once, synchronously, before the app's first paint (see
// src/main.tsx) - never at this module's top level, so importing
// ScadaTheme.ts (e.g. from a Vitest test running under Node, with no
// `document`) stays side-effect-free.
export function applyScadaCssVariables(target: HTMLElement = document.documentElement): void {
  target.style.setProperty('--scada-canvas-bg', COLOR_CANVAS_BACKGROUND);
  target.style.setProperty('--scada-outline', COLOR_OUTLINE);
  target.style.setProperty('--scada-panel', COLOR_PANEL);
  target.style.setProperty('--scada-bevel-light', COLOR_BEVEL_LIGHT);
  target.style.setProperty('--scada-bevel-dark', COLOR_BEVEL_DARK);
  target.style.setProperty('--scada-value-field', COLOR_VALUE_FIELD);
  target.style.setProperty('--scada-white', COLOR_WHITE);
  target.style.setProperty('--scada-energized', COLOR_ENERGIZED);
  target.style.setProperty('--scada-de-energized', COLOR_DE_ENERGIZED);
  target.style.setProperty('--scada-run', COLOR_RUN);
  target.style.setProperty('--scada-alarm', COLOR_ALARM);
  target.style.setProperty('--scada-lamp-lit', COLOR_LAMP_LIT);
  target.style.setProperty('--scada-water', COLOR_WATER);
  target.style.setProperty('--scada-ventilation-active', VENTILATION_ACTIVE);
  target.style.setProperty('--scada-ventilation-inactive', VENTILATION_INACTIVE);
  target.style.setProperty('--scada-font-ui', FONT_UI);
  target.style.setProperty('--scada-font-value', FONT_VALUE);
  target.style.setProperty('--scada-font-size-base', `${FONT_SIZE_BASE}px`);
  target.style.setProperty('--scada-font-size-small', `${FONT_SIZE_SMALL}px`);
  target.style.setProperty('--scada-font-size-title', `${FONT_SIZE_TITLE}px`);
}
