"""Studio's own chrome stylesheet.

Task "Studio: wyostrzenie stylu i układu do poziomu narzędzia
profesjonalnego", Problem 2: "Powierzchnie są płaskie. Win98 to system
wypukłości i wklęsłości, nie paleta kolorów." Every border/padding value
below is copied from runtime/epw_os/gui/style.py's own `_STYLE_TEMPLATE`
- read there before changing anything here, not invented. Two real
differences from that file, both because Studio's situation differs
from runtime's, not because the values differ:

  1. runtime's QSS is the WHOLE app's stylesheet (QApplication-level,
     rebuilt per theme). Studio already has an app-wide stylesheet it
     must coexist with - logic_studio.app.apply_classic_style(), which
     both LogicPanel and studio/main.py apply to the whole QApplication
     (GRANICE: "nie przepisuj Logic Studio" - that function is not
     touched here). This module's STUDIO_CHROME_QSS is instead set
     directly on StudioMainWindow itself (widget-level setStyleSheet(),
     not QApplication-level) - Qt resolves a widget's own stylesheet
     ahead of an inherited QApplication one for matching selectors, so
     this repaints Studio's OWN chrome (menu bar, both toolbars, the
     tree, the status bar) with runtime's 2px/panel_bg grammar while
     leaving Logic Studio's and Synoptic's own internal widgets exactly
     as apply_classic_style()/the SCADA overlay already render them -
     untouched, per GRANICE.
  2. runtime's QToolButton relies entirely on Qt's native "windows"
     QStyle for hover/pressed rendering (no QToolButton rule in
     style.py at all) - safe there because nothing else on that
     QApplication defines a competing QToolButton QSS rule. Studio
     can't rely on that: apply_classic_style() DOES set its own
     QToolButton rule (1px borders, no vertical separators) app-wide,
     and since that stylesheet is applied first and this one is scoped
     to StudioMainWindow specifically, it would otherwise win for any
     selector this file doesn't also state explicitly. So this file
     spells out QToolButton's raised/hover/pressed states itself,
     using the same 2px bevel/button_shadow tokens as every other
     raised surface below - not a new convention, just an explicit
     restatement of the existing one where a silent inherited rule
     would otherwise undercut it.
"""

# STUDIO_UI_STANDARD.md section 1, quoted from epw_os/core/themes.py's
# "industrial" theme - the literal values, not re-derived.
_WINDOW_BG = "#C0C0C0"
_PANEL_BG = "#D4D0C8"
_FIELD_BG = "#FFFFFF"
_TEXT = "#000000"
_TEXT_DISABLED = "#808080"
_BEVEL_LIGHT = "#FFFFFF"
_BEVEL_SHADOW = "#808080"
_BUTTON_SHADOW = "#404040"
_GRID_LINE = "#808080"
_ACCENT_BG = "#000080"
_ACCENT_TEXT = "#FFFFFF"

STUDIO_CHROME_QSS = f"""
/* Task "Studio: wyostrzenie stylu" Problem 2 - runtime/epw_os/gui/
   style.py's own grammar, ported to Studio's own chrome. Border widths,
   padding, and which side gets light vs shadow are copied verbatim from
   that file - only the selectors differ (StudioMainWindow's own
   objectName'd widgets, not every QWidget app-wide). */

QMainWindow#StudioMainWindow {{
    background-color: {_WINDOW_BG};
}}

/* --- Menu bar / menus: runtime style.py's QMenuBar/QMenu rules --- */
QMainWindow#StudioMainWindow > QMenuBar {{
    background-color: {_PANEL_BG};
    border-bottom: 2px outset {_BEVEL_LIGHT};
}}
QMainWindow#StudioMainWindow > QMenuBar::item {{
    background-color: transparent;
    padding: 2px 6px;
}}
QMainWindow#StudioMainWindow > QMenuBar::item:selected {{
    background-color: {_ACCENT_BG};
    color: {_ACCENT_TEXT};
}}
QMainWindow#StudioMainWindow QMenu {{
    background-color: {_PANEL_BG};
    border: 2px outset {_BEVEL_LIGHT};
}}
QMainWindow#StudioMainWindow QMenu::item {{
    padding: 3px 20px;
}}
QMainWindow#StudioMainWindow QMenu::item:selected {{
    background-color: {_ACCENT_BG};
    color: {_ACCENT_TEXT};
}}
QMainWindow#StudioMainWindow QMenu::separator {{
    height: 2px;
    background: {_BEVEL_SHADOW};
    margin: 2px 4px;
}}

/* --- Toolbars: runtime style.py's QToolBar rule, both of Studio's
   own bars (#SharedToolbar fixed, #ContextToolbar per-aspect) --- */
QToolBar#SharedToolbar, QToolBar#ContextToolbar {{
    background-color: {_PANEL_BG};
    border-bottom: 2px solid {_BEVEL_SHADOW};
    padding: 2px;
    spacing: 2px;
}}
QToolBar#SharedToolbar::separator, QToolBar#ContextToolbar::separator {{
    background: {_BEVEL_SHADOW};
    width: 2px;
    margin: 2px 3px;
}}

/* --- Toolbar buttons: not in runtime's style.py at all (nothing else
   on that QApplication competes for QToolButton, so native "windows"
   QStyle rendering was enough there) - restated explicitly here,
   because it must win over apply_classic_style()'s own 1px
   QToolButton rule for Studio's two bars specifically.

   Problem 2's own wording is literal and followed literally: "wypukłe
   W SPOCZYNKU, WCIŚNIĘTE po kliknięciu, podświetlone pod kursorem" -
   three distinct states, not two. Raised is the RESTING bevel (not
   hover-only, unlike the flat-until-hover convention some Win98
   toolbars use) - same 2px light/button_shadow bevel QPushButton uses
   below. Hover adds a background tint on top of that same raised
   bevel (the "podświetlone" - highlighted - state Problem 2 names
   separately from pressed). Pressed/checked inverts the bevel and
   nudges content by 1px, the identical QPushButton:pressed convention
   from STUDIO_UI_STANDARD.md section 3. --- */
QToolBar#SharedToolbar QToolButton, QToolBar#ContextToolbar QToolButton {{
    background-color: {_PANEL_BG};
    border: 2px solid;
    border-top-color: {_BEVEL_LIGHT};
    border-left-color: {_BEVEL_LIGHT};
    border-right-color: {_BUTTON_SHADOW};
    border-bottom-color: {_BUTTON_SHADOW};
    padding: 2px;
}}
QToolBar#SharedToolbar QToolButton:hover, QToolBar#ContextToolbar QToolButton:hover {{
    background-color: #DCD8CC;
}}
QToolBar#SharedToolbar QToolButton:pressed, QToolBar#ContextToolbar QToolButton:pressed,
QToolBar#SharedToolbar QToolButton:checked, QToolBar#ContextToolbar QToolButton:checked {{
    border-top-color: {_BUTTON_SHADOW};
    border-left-color: {_BUTTON_SHADOW};
    border-right-color: {_BEVEL_LIGHT};
    border-bottom-color: {_BEVEL_LIGHT};
    padding-top: 3px;
    padding-left: 3px;
    background-color: #B8B4A8;
}}
QToolBar#SharedToolbar QToolButton:disabled, QToolBar#ContextToolbar QToolButton:disabled {{
    color: {_TEXT_DISABLED};
}}

/* --- Tree: runtime style.py's QTableWidget/QTreeWidget rule - sunken
   (shadow top/left, light bottom/right), field_bg content --- */
QTreeWidget#ProjectTree {{
    background-color: {_FIELD_BG};
    color: {_TEXT};
    border: 2px solid;
    border-top-color: {_BEVEL_SHADOW};
    border-left-color: {_BEVEL_SHADOW};
    border-right-color: {_BEVEL_LIGHT};
    border-bottom-color: {_BEVEL_LIGHT};
    outline: none;
}}
QTreeWidget#ProjectTree::item:selected {{
    background-color: {_ACCENT_BG};
    color: {_ACCENT_TEXT};
}}

/* --- Status bar: runtime style.py's QStatusBar rule - sunken item
   wells, a raised top edge on the bar itself --- */
QMainWindow#StudioMainWindow > QStatusBar {{
    background-color: {_PANEL_BG};
    border-top: 2px solid {_BEVEL_LIGHT};
}}
QMainWindow#StudioMainWindow > QStatusBar::item {{
    border: 1px inset {_BEVEL_SHADOW};
}}
QMainWindow#StudioMainWindow > QStatusBar QLabel {{
    padding: 2px 6px;
    background: transparent;
}}
"""
