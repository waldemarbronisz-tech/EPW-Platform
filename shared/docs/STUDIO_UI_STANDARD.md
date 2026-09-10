# EPW Studio UI Standard (Windows 98 / retro-industrial)

**Authoritative source: `runtime/epw_os/gui/` - specifically
`epw_os/core/themes.py`'s `"industrial"` theme (index 0, the default,
and the one with a hard "must render pixel-identical" requirement in
its own source comment) and `epw_os/gui/style.py`'s QSS template built
from it.** This is the most developed Win98 implementation on the
whole platform - real tables, a real navigation tree, real dialogs,
real form fields, all already shipped and in daily use. Everything
below is quoted or directly derived from those two files (read-only -
`runtime/` was never modified to produce this document).

`studio/logic/logic_studio/app.py`'s `apply_classic_style()` and
`studio/synoptic`'s own theme (`ScadaTheme.ts`/`index.css`) are
reconciled against this runtime standard, not the other way around -
noted per-section below where they already agree, and where Stage 2
will need to tune them to match. **Goal, stated directly in the task
that produced this document: someone moving from Studio to the runtime
control panel should feel it is the same product**, not two related
but visibly different programs.

---

## 1. Palette

Quoted directly from `epw_os/core/themes.py`'s `"industrial"` theme
(`THEMES[0]`):

| Token (runtime name) | Hex | Role |
|---|---|---|
| `window_bg` | `#C0C0C0` | Outermost window/desktop background |
| `panel_bg` | `#D4D0C8` | Panels, frames, menus, toolbars, headers, dialogs - the authentic classic-Windows "3D Objects" tone, warmer than `window_bg` (a real, deliberate distinction runtime already makes - **do not collapse these into one grey**, that is a common but incorrect simplification of this look) |
| `field_bg` | `#FFFFFF` | Text fields, tables, trees, LCD-style value displays' content area |
| `text` | `#000000` | Body text |
| `text_disabled` | `#808080` | Disabled control text |
| `bevel_light` | `#FFFFFF` | Raised-edge light side (top+left) |
| `bevel_shadow` | `#808080` | Raised-edge shadow side (bottom+right) - also table gridlines |
| `button_shadow` | `#404040` | The DARKER of two shadow tones, used specifically on buttons (a 3-tone bevel: light / mid-shadow `bevel_shadow` / dark-shadow `button_shadow` - buttons get the harder, darker shadow; frames/tables/menus get the softer one) |
| `grid_line` | `#808080` | Table/tree gridlines (same value as `bevel_shadow`, kept as its own token because it means something different) |
| `accent_bg` | `#000080` | Selection / active-item background (classic Win98 navy) |
| `accent_text` | `#FFFFFF` | Text on `accent_bg` |
| `dialog_border` | `#000000` | Flat dialog outline |
| `spin_pressed_bg` | `#A0A0A0` | Spin-button pressed state |

**Reconciliation with `studio/`:**
- Logic Studio's `apply_classic_style()` uses a single `#C0C0C0` for
  everything panel-shaped - runtime's two-tone `window_bg`/`panel_bg`
  split is more authentic and more detailed; **Stage 2 should adopt
  the two-tone split in Logic Studio too** (its own window background
  becomes `window_bg`, its panels/menus/toolbar/status bar become
  `panel_bg`).
- Logic Studio's selection highlight is already exactly `#000080`/
  `#FFFFFF` - matches `accent_bg`/`accent_text` exactly, no change
  needed.
- Logic Studio has no third shadow tone (`button_shadow`) - its
  buttons use plain `bevel_shadow` (`#808080`) for the dark bevel side.
  Runtime's buttons specifically use the darker `#404040`. **Stage 2
  should adopt `button_shadow` for buttons**, keeping `bevel_shadow`
  for frames/menus/tables - this is what makes runtime's buttons read
  as slightly crisper than its frames, a real, visible distinction.
- Synoptic's theme has no equivalent of `panel_bg`/`button_shadow` at
  all (its `--sys-*` layer only has light/dark/darker, collapsed from
  three underlying `--scada-*` tones that are two-tone, not three) -
  the overlay in section 6 introduces the missing third tone.

**Out of scope for this palette** - runtime's own `STATE_KEYS` (`state_ok`,
`state_alarm`, `state_warning`, etc.) are process/alarm colors, not
chrome - Studio has no process state to color (GRANICE also already
established this for Synoptic's own domain colors - same principle,
same reason: a color that means something on a live process display
must never become a decorative chrome accent).

## 2. Typography

- **Font family**: `"Tahoma", "MS Sans Serif", sans-serif` - quoted
  directly, verbatim, from `style.py`'s `_STYLE_TEMPLATE` (used on
  every `QWidget` and repeated explicitly on `QTableWidget`/
  `QTreeWidget`). Studio standard face list, folding in Studio's own
  existing fallbacks so nothing currently displayable stops resolving:
  **`Tahoma, "MS Sans Serif", "Segoe UI", Verdana, "DejaVu Sans",
  sans-serif`**.
- **Base UI size**: **11px** - quoted directly (`font-size: 11px;` on
  `QWidget` and again on the table/tree rule). This is runtime's own
  actual shipped size, and now the Studio standard's base size, in
  preference to Logic Studio's own current `9pt` (`apply_classic_style`) -
  **reconciliation**: runtime wins per this document's own authority
  rule. 11px at a standard 96dpi screen is ~8.25pt - close to but not
  identical to Logic Studio's 9pt; Stage 2 should move Logic Studio to
  11px exactly, not split the difference.
- **Page header**: 14px bold, `accent_bg`/`accent_text` background,
  5px padding (`QLabel#PageHeader`).
- **Section header**: 12px bold, `accent_bg`/`accent_text`, 2px padding
  (`QLabel#SectionHeader`).
- **Monospace** (values/telemetry/console): `'Consolas', 'Courier New'`,
  12px - quoted from the `QTableWidget#EventTable` rule (runtime's
  console-style table). Synoptic's own `FONT_VALUE` (`Consolas,
  "DejaVu Sans Mono", monospace`) already agrees closely enough to
  keep as-is.

## 3. Borders and bevels (the Win98 3D look)

Quoted directly from `style.py` - runtime uses a **uniform 2px border**
for every chrome element (not a 1px/2px split by element type):

- **Raised** (frames, buttons, menus, table headers - the resting
  state of anything clickable or panel-shaped): `border: 2px solid`,
  `bevel_light` on top+left, the shadow tone on bottom+right (`button_shadow`
  for buttons specifically - see section 1 - `bevel_shadow` for
  everything else raised).
- **Pressed**: the same border INVERTED (shadow top+left, `bevel_light`
  bottom+right) - quoted exactly: `QPushButton:pressed` also nudges
  content by exactly **1px** (`padding-top: 5px; padding-left: 5px`
  against the resting `padding: 4px` - i.e. +1px on press, not a
  larger jump).
- **Sunken** (table/tree content area, form fields, LCD labels, alarm
  list): the raised bevel INVERTED at rest, no press state (nothing to
  press - it's a permanently recessed well). Runtime uses two ways to
  express this, both valid and already in the QSS: an explicit 4-side
  color assignment (`QTableWidget`/`QTreeWidget`: shadow top/left,
  light bottom/right) or Qt's own `inset` border-style keyword, which
  computes the same look automatically (`QComboBox`/`QSpinBox`/
  `QLineEdit`: `border: 2px inset {bevel_shadow}`; `QLabel#LCD`
  likewise). Prefer `inset`/`outset` keywords for new chrome - shorter,
  and it is what runtime itself already prefers for form fields.
- **Table header cells** (`QHeaderView::section`): raised (`2px
  outset`, `panel_bg` background, bold text) - a header cell is a
  clickable-looking control, styled like a button, not like the sunken
  content below it.
- **Menu popups**: `panel_bg` background, `2px outset {bevel_light}`
  border (quoted from `QMenu`) - simpler than Logic Studio's own
  QMenu rule (which hard-codes a 1px light + 2px black asymmetric
  border); **Stage 2 adopts runtime's simpler, uniform `2px outset`.**
- **Border weight, restated plainly**: **2px everywhere** in this
  standard - chrome, content wells, table headers, dialogs, menus. This
  is the one point where runtime is simpler than either `studio/`
  theme today (both of which mix 1px and 2px by element) - adopt 2px
  uniformly, it is what makes runtime's own look read as "chunky" Win98
  rather than a thin modern flat style.

## 4. Control heights and spacing

Quoted directly from runtime source (`nav_tree.py`, `table_helpers.py`,
`style.py`):

| Element | Value | Source |
|---|---|---|
| Navigation tree row height | **24px** | `nav_tree.py`'s `ROW_HEIGHT` constant (deliberately tightened from an earlier 32px - see that file's own comment) |
| Data table row height | **~30px** (auto-sized; not a hard constant) | `table_helpers.py`'s own comment on `TABLE_BUTTON_HEIGHT`'s sizing rationale |
| Table-cell button height (Force/Notes/Configure/Acknowledge) | **22px** | `table_helpers.py`'s `TABLE_BUTTON_HEIGHT` |
| Form field min-height (`QComboBox`/`QSpinBox`/`QLineEdit`) | **20px** | `style.py`'s form-field rule |
| Button padding (rest / pressed) | **4px / 5px** (top+left only on press) | `style.py`'s `QPushButton` rule |
| Table-cell button padding | **2px 6px** | `table_helpers.py`'s `apply_table_button_style()` |
| General chrome padding (menu items, status bar items, table cells, page/section headers minimum) | **2px** | recurring atomic unit across nearly every rule in `style.py` |
| Menu bar / menu item padding | **2px 6px** | `style.py`'s `QMenuBar::item` |
| Spin-button stepper size | **15px wide x 10px tall** | `style.py`'s `QSpinBox::up-button`/`down-button` |

**Atomic spacing unit: 2px** (confirmed as the single recurring value
across nearly every padding/margin in `style.py` - the same conclusion
the Logic-Studio-only draft of this document reached independently;
runtime's own source reinforces it as the platform-wide unit, not a
coincidence of one file).

## 5. Tables: header and cell style

Quoted directly from `style.py`'s `QTableWidget, QTreeWidget` rule set
(this is the literal "styl nagłówków tabel" requested):

- Header cells (`QHeaderView::section`): `panel_bg` background, raised
  2px bevel (`bevel_light` top/left, `bevel_shadow` bottom/right),
  2px padding, **bold** text.
- Body: `field_bg` (white) background, sunken 2px bevel around the
  whole table (`bevel_shadow` top/left, `bevel_light` bottom/right),
  gridlines in `grid_line`.
- Cell (`::item`): 1px `grid_line` border on bottom+right only (the
  top/left border of one cell IS the previous cell's bottom/right -
  standard shared-gridline construction), 2px padding.
- Selected cell/row: `accent_bg` background, `accent_text` text -
  same selection convention as everywhere else in this standard, never
  a table-specific one.
- A themed table needing per-row/per-cell background colors beyond
  selection (e.g. an alarm row) MUST use `table_helpers.py`'s own
  `ItemBackgroundDelegate` - confirmed empirically in that file's own
  docstring that plain `QTableWidgetItem.setBackground()` silently does
  nothing once any `::item` QSS rule exists (which this standard's own
  `::item` rule above guarantees). Anything Stage 2 builds with
  per-cell coloring needs this delegate, not `setBackground()` alone.

## 6. Tree (the project tree - `EKRANY`/`LOGIKA`)

Quoted/derived from `nav_tree.py` (a custom-painted tree - not a plain
QSS-styled `QTreeWidget`, though Studio's own two-flat-item tree does
not need that much machinery):

- Row height: **24px** (section 4).
- Row background: `field_bg` (white) for a plain item; `panel_bg` for
  a group header row (Studio's tree has no groups today - two flat
  items - but if the future Cards/Points/etc. branches ever arrive
  with sub-items, this is the established convention to reuse, not
  invent a new one).
- Selected row: `accent_bg`/`accent_text` - identical to every other
  selection surface.
- Row separator/accent lines use `bevel_light`/`bevel_shadow`, same
  bevel language as everything else, not a tree-specific pair.
- Icons: 16x16px (task 2.4 asks for icons where Studio's tree has none
  today). `nav_tree.py`'s own icons are custom-painted glyphs, not
  image assets, matching Logic Studio's own procedural
  `icons.action_icon()` convention (`logic_studio/ui/icons.py`) - two
  independent parts of this platform already agree on "icons are drawn
  in code, not shipped as image files"; Studio's two tree icons should
  be built the same way.

## 7. Buttons and form fields

- **Buttons** (`QPushButton`): `panel_bg` background, 2px raised bevel
  using `button_shadow` (not the softer `bevel_shadow`) for the dark
  side, 4px padding (5px top/left when pressed - bevel inverts too),
  disabled text in `text_disabled`.
- **Table-cell buttons** specifically (a narrower context): same bevel
  logic, 22px fixed height, 2px 6px padding - `table_helpers.py`'s
  `apply_table_button_style()` - and its own documented reason for
  existing: a button with ANY local `setStyleSheet()` stops inheriting
  the app-wide `QPushButton` rule's border, so any Studio button that
  needs its own per-instance styling (a color variant, a fixed size)
  must redeclare the FULL bevel locally, every time - never assume the
  ancestor rule's border survives a partial local override.
- **Form fields** (`QComboBox`/`QSpinBox`/`QDoubleSpinBox`/`QLineEdit`):
  `field_bg` background, 2px inset bevel (`bevel_shadow`), 2px padding,
  20px min-height.
- **Spin steppers**: 15x10px raised buttons with a small (9x5px)
  triangle glyph, pressed state uses `spin_pressed_bg`, disabled state
  uses `window_bg`. Runtime renders the arrow glyphs as tiny pre-made
  PNGs rather than a QSS border-triangle trick (documented in
  `style.py` as a reliability fix, not a stylistic choice) - Studio
  should do the same if it ever needs a stepper control, not
  re-attempt the CSS-border-triangle approach runtime already found
  unreliable.

## 8. Dialogs

- `QDialog#IndustrialDialog`: `panel_bg` background, flat 2px solid
  `dialog_border` (`#000000`) outline - no bevel, a plain outline, the
  one place in this whole standard that is deliberately flat rather
  than raised/sunken (a dialog frame is not a control, it doesn't need
  a press state or a "raised" affordance).
- Buttons inside a dialog are ordinary `QPushButton`s (section 7) - no
  separate dialog-button style exists in runtime, and Studio should not
  invent one.

## 9. Applying this to Synoptic: which CSS variables move, which never do

Synoptic's theme is already centralized behind CSS custom properties,
set once at startup by `applyScadaCssVariables()` writing inline styles
onto `document.documentElement` - confirmed empirically in the Stage 1
report that re-setting the same properties later re-cascades live, no
rebuild needed. The chrome-relevant subset (confirmed against
`index.css`'s own `--sys-*` aliases, which already separate chrome
from domain color) maps onto this standard as follows:

| Variable | New value | Runtime source |
|---|---|---|
| `--scada-panel` | `#D4D0C8` | `panel_bg` |
| `--scada-bevel-light` | `#FFFFFF` | `bevel_light` |
| `--scada-bevel-dark` | `#808080` | `bevel_shadow` |
| `--scada-outline` | `#000000` | `text` |
| `--scada-white` | `#FFFFFF` | literal white |
| `--scada-value-field` | `#FFFFFF` | `field_bg` |
| `--scada-font-ui` | `Tahoma, "MS Sans Serif", "Segoe UI", Verdana, "DejaVu Sans", sans-serif` | typography |
| `--scada-font-size-small` | `11px` | base size |
| `--scada-font-size-base` | `11px` | runtime does not scale a "body" size up from base the way Synoptic's own three-tier system does - **reconciliation**: keep Synoptic's own 3-tier ratio (base/body/title) scaled off the new 11px base rather than flattening to one size everywhere, since the underlying components already expect 3 distinct sizes to exist |
| `--scada-font-size-title` | ~13px (11px * 1.15, keeping Synoptic's own existing ratio) | derived, see above |

New variables the overlay must additionally define (no `--scada-*`
source - two extra chrome tones runtime has that Synoptic's simpler
two-tone system does not):
`--sys-window-bg: #C0C0C0` (distinct from panel), `--sys-button-shadow:
#404040` (for anything Stage 2 restyles as a button rather than a
panel), `--sys-highlight: #000080`, `--sys-highlight-text: #FFFFFF`
(today `index.css` aliases `--sys-highlight` to `--scada-outline`,
i.e. black - this is the one correction, not just a retint, this
standard makes to Synoptic's current look).

**Variables this standard NEVER touches** (domain-meaningful, per
`ScadaTheme.ts`'s own module comment: "3D bevel shading is deliberately
kept to interface chrome only... the canvas and the symbols on it stay
flat"): `--scada-canvas-bg`, `--scada-energized`, `--scada-de-energized`,
`--scada-run`, `--scada-alarm`, `--scada-lamp-lit`, `--scada-water`,
`--scada-ventilation-active`, `--scada-ventilation-inactive`,
`--scada-font-value` (monospace values keep their own font regardless
of chrome theme) - this list is unchanged from the reasoning already
established against Synoptic's own source, only the target hex values
above changed to track runtime instead of Logic Studio.

The `.dropdown` popup styling (currently a `box-shadow`, not a border)
is the one place Synoptic's CSS RULES - not just variable values -
differ enough from this standard that the overlay needs an actual rule
override (`2px outset` per section 3), not just new variable values -
documented here so it is not a surprise when Stage 2 writes it.
