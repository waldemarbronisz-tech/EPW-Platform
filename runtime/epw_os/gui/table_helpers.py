"""Shared setup for the program's data tables and trees.

Column widths must stay user-adjustable - the operator drags a header
border to resize. That rules out ``Stretch`` and ``ResizeToContents``
resize modes (both lock the section so it can't be dragged), so every
table uses ``Interactive`` mode seeded with sensible starting widths.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHeaderView, QStyledItemDelegate


# Task ("popraw wyglad przyciskow w komorkach tabel"): a fixed height every
# table-cell button (Force/Notes/Configure/Acknowledge) now shares, chosen
# to fit inside the row heights these tables already have (Digital Inputs/
# Control Outputs currently auto-size to 30px; a 22px button plus a 2px
# margin on each side is 26px, comfortably inside that with no row growth -
# GRANICE: "nie rozpychaj wierszy"). Was 20px (Notes) / 16px (Force/
# Configure) / unset-auto (Acknowledge) before - inconsistent between
# button "kinds" even though each was internally consistent row-to-row.
TABLE_BUTTON_HEIGHT = 22


def apply_table_button_style(button, colors=None, extra_css=""):
    """Explicit classic-Windows-98 raised-bevel look for a button
    embedded in a table cell, plus TABLE_BUTTON_HEIGHT.

    Why this redeclares the border instead of just relying on the
    app-wide QPushButton rule (style.py) these buttons would otherwise
    inherit: every one of them already needs its OWN setStyleSheet()
    call (for its color and/or size), and once a button has any local
    stylesheet of its own, Qt's style engine does NOT reliably fall
    back to the ancestor rule's `border` for whatever that local sheet
    leaves unset - confirmed empirically (a button styled with only
    `color: ...; padding: ...;` rendered completely flat, no bevel at
    all, even though the inherited QPushButton rule clearly sets one).
    That is the actual mechanism behind this task's "plaskie, bez
    wypuklosci" complaint - not a missing style, an overridden one.
    Redeclaring the full bevel locally, every time, is the reliable fix,
    and keeps colors themed (Task: pull from themes.py, not hardcoded) -
    :pressed inverts the same four border colors, the classic Win98
    "sunken on click" effect.

    `colors`: current_colors() dict, if the caller already has it handy
    (avoids re-fetching per row in a loop); fetched fresh otherwise.
    `extra_css`: appended after the bevel rule so a caller can still add
    its own touch (e.g. Force's red text) without needing to repeat the
    border itself."""
    from epw_os.gui.theme_manager import current_colors as _current_colors
    c = colors if colors is not None else _current_colors()
    button.setStyleSheet(f"""
        QPushButton {{
            background-color: {c['panel_bg']};
            border: 2px solid;
            border-top-color: {c['bevel_light']};
            border-left-color: {c['bevel_light']};
            border-right-color: {c['button_shadow']};
            border-bottom-color: {c['button_shadow']};
            padding: 2px 6px;
            color: {c['text']};
        }}
        QPushButton:pressed {{
            border-top-color: {c['button_shadow']};
            border-left-color: {c['button_shadow']};
            border-right-color: {c['bevel_light']};
            border-bottom-color: {c['bevel_light']};
        }}
        {extra_css}
    """)
    button.setFixedHeight(TABLE_BUTTON_HEIGHT)


def style_transparent_cell_container(container):
    """A QWidget used only to center a table-cell button (Force/
    Configure, wrapped so their button can be smaller than the row and
    still centered) must be invisible itself - without this it inherits
    the generic QWidget rule's own background-color, painting a solid,
    differently-shaded box behind the button that reads as a mismatched
    frame around it rather than a clean cell."""
    container.setStyleSheet("background: transparent; border: none;")


def set_resizable_columns(header: QHeaderView, default_widths, stretch_last=False):
    """Make every column in `header` user-resizable (drag the border) and
    give each a starting width.

    `default_widths`: one width per column; a value of 0 leaves that
    column at Qt's default width. `stretch_last`: when True the final
    column auto-fills the remaining space (and is then not draggable) -
    left False so *all* columns can be dragged.
    """
    header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    header.setStretchLastSection(stretch_last)
    for i, width in enumerate(default_widths):
        if width:
            header.resizeSection(i, width)


def set_header_tooltips(table, tooltips):
    """Task: podpowiedzi - "naglowki kolumn, zwlaszcza mniej oczywiste".
    `tooltips`: one string per column, in the same order as the table's
    columns (call right after setHorizontalHeaderLabels(), which is what
    creates the QTableWidgetItem each tooltip attaches to). An empty
    string or None skips that column - a page passes that for a header
    whose text already says everything (Task: "nie dodawaj tam, gdzie
    etykieta mowi wszystko"), rather than every page repeating that
    skip-logic itself."""
    for i, text in enumerate(tooltips):
        if not text:
            continue
        item = table.horizontalHeaderItem(i)
        if item is not None:
            item.setToolTip(text)


class ItemBackgroundDelegate(QStyledItemDelegate):
    """Bug fix: QTableWidgetItem.setBackground() silently does nothing
    once the table's stylesheet styles ``::item`` for ANY property
    (style.py's QTableWidget::item rule sets border-bottom/border-right/
    padding - no color/background-color, but that's enough to trigger
    this) - confirmed empirically: with this app's real stylesheet
    applied, an item's own background stays the table's plain default
    regardless of setBackground(), while setForeground() keeps working
    normally. A row meant to be highlighted (e.g. an intrusion line
    showing VIOLATED, or a zone in ALARM) then renders its intended
    LIGHT foreground color (accent_text) on the table's own plain
    background instead of the intended dark highlight - on a light
    theme that's light-on-light, unreadable until the row is selected
    (QTableWidget::item:selected DOES explicitly set both background-
    color and color in its own QSS rule, which is why selecting a row
    was the only way to see the text).

    Fix: paint Qt::BackgroundRole ourselves, directly, before handing
    off to the normal (QSS-driven) paint - which still correctly
    handles everything else, foreground included, and still paints the
    selection highlight on top when a cell is selected (confirmed: the
    style's own selected-state fill draws after this delegate's
    manual background fill, so it's never hidden underneath).
    setItemDelegate() on a table applies this only to THAT table -
    no other table's rendering is affected by using it on one."""

    def paint(self, painter, option, index):
        bg = index.data(Qt.ItemDataRole.BackgroundRole)
        if bg is not None:
            painter.save()
            painter.fillRect(option.rect, bg)
            painter.restore()
        super().paint(painter, option, index)
