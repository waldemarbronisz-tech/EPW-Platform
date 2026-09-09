"""Left navigation panel, styled to match the Windows 98 Explorer
directory tree (Task: "Poprawic wyglad drzewa nawigacji, zeby wiernie
odpowiadalo drzewu z Eksploratora Windows 98" - a follow-up visual-only
pass on top of the tree built for "Przebudowac lewe menu nawigacji na
drzewo w stylu Windows 98"; structure/grouping/feature-config wiring is
untouched, only how it's painted).

Every color comes from the active theme (epw_os/core/themes.py) via
get_theme_manager().current_colors() - GRANICE: "Kolory z themes.py -
ma dzialac we wszystkich pieciu motywach", nothing here hardcodes a
color literal. No new theme keys were needed - every token used below
(state_caution/text/field_bg/grid_line/panel_bg/bevel_light/
bevel_shadow/accent_bg/accent_text) already exists in themes.py.

WHY A CUSTOM DELEGATE, NOT QSS ::branch RULES: this app's own QSS
::branch technique for indicators (see epw_os/gui/style.py's own
comment on the spin-box up/down arrows) relies on small, FIXED-COLOR
PNG glyphs, deliberately never recolored per theme, because those
always sit on a "mid-toned" button face guaranteed readable either way.
Everything painted here - the folder/page icons, the toggle box, the
connector lines, the selection band - sits on tree backgrounds that
range from near-black (High Contrast/Night) to near-white (Industrial/
SimCity 2000), so a single fixed color can't work for any of it. Same
"a stylesheet can't express this, so a delegate paints it directly"
reasoning epw_os/gui/table_helpers.py's ItemBackgroundDelegate/
StateColorItemDelegate already document for table cells applies here,
one level up.
"""
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QStyledItemDelegate, QStyle
from PySide6.QtCore import Qt, QRect, QSize, QPoint, Signal
from PySide6.QtGui import QColor, QPen, QPolygon, QPainter

from epw_os.gui.theme_manager import get_theme_manager
from epw_os.gui import window_state
from epw_os.core.nav_model import build_nav_tree, first_page_id
from epw_os.i18n import tr

# --- sizing (Task 2: "drzewo jest CIASNE - wysokosc wiersza ledwo
# wieksza od wysokosci tekstu, minimalne odstepy") ---------------------
#
# Tightened from the previous pass's TOGGLE_SIZE=20/ROW_HEIGHT=32 (which
# read as a modern, spaced-out list, not an Explorer tree) down to
# something close to the era's own density, WITHOUT literally copying
# its ~9px toggle box / ~18px row - see mousePressEvent()'s own comment
# for how the touch-target compromise this forces is actually resolved
# (a generous invisible hit zone around a small, authentic-looking
# glyph, not a bigger glyph). Documented in SESSION_REPORT.md per the
# task's own explicit request.
TOGGLE_SIZE = 13   # the drawn [+]/[-] glyph box - visual size only
ICON_SIZE = 16     # Task 3: "ikony 16x16"
ROW_HEIGHT = 24    # down from 32 - tight, but each row is still a full
                   # touch target for navigation (a miss just lands on
                   # the neighbouring row, never a wrong control action)
_INDENT = 22       # width of the toggle/connector column - also IS the
                   # toggle's touch-hit column width (see mousePressEvent)
_LEFT_MARGIN = 4
_TEXT_GAP = 4      # icon -> text, and toggle -> icon, spacing

# item.data(0, ...) roles - Qt.UserRole and up are free for application use.
_PAGE_ID_ROLE = Qt.ItemDataRole.UserRole
_ATTENTION_ROLE = Qt.ItemDataRole.UserRole + 1
_GROUP_ID_ROLE = Qt.ItemDataRole.UserRole + 2  # set only on a real (multi-child) group's own top-level item

ATTENTION_NONE = None
ATTENTION_WARNING = "warning"
ATTENTION_ALARM = "alarm"


def _display_case(text: str) -> str:
    """Task 7: "w Windows 98 pozycje drzewa pisane sa normalnie, nie
    wersalikami" - a DISPLAY-ONLY transform applied here, in the tree
    widget alone: the underlying nav.* translation values stay
    ALL-CAPS (page headers and FeatureConfigDialog's own checkboxes -
    Task: "nie w naglowkach stron" - both still read them directly and
    must stay exactly as they are). Sentence case (str.capitalize()),
    not Title Case per word: this app's menu bar already uses sentence-
    style casing ("Jezyk...", "Wygaszanie ekranu...") - matching that
    is MORE consistent with the rest of the interface than capitalizing
    every word would be, and Polish phrases read correctly this way
    ("Wejscia cyfrowe", not the grammatically odd "Wejscia Cyfrowe").
    See SESSION_REPORT.md for the full reasoning."""
    return text.capitalize() if text else text


class NavTreeDelegate(QStyledItemDelegate):
    def __init__(self, tree: "NavTreeWidget", parent=None):
        super().__init__(parent)
        self.tree = tree

    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        return QSize(size.width(), ROW_HEIGHT)

    def paint(self, painter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)  # crisp 1px lines/dots, Task 4
        colors = get_theme_manager().current_colors()
        item = self.tree.itemFromIndex(index)
        rect = option.rect
        is_top_level = not index.parent().isValid()
        is_group = item.childCount() > 0
        selected = bool(option.state & QStyle.StateFlag.State_Selected)

        # --- background: ONE flat color for the whole panel (Task 1:
        # "cala strukture tworza wylacznie linie, wciecia i przelaczniki
        # [+]/[-]" - no per-group/per-item shading at all anymore).
        # Always painted first, selected or not, so the toggle box and
        # connector lines - drawn next, further left than the selection
        # band ever reaches - never sit on stale pixels from a
        # previous paint.
        painter.fillRect(rect, QColor(colors["field_bg"]))

        # --- dotted connector line (Task 4: "linie ida pionowo wzdluz
        # calej galezi i poziomo do kazdego wezla" + "wyraznie
        # odcinajace sie od tla") - a tight, explicit 1-on/1-off dash
        # (Qt's built-in DotLine pattern reads as barely-there once pen
        # width/antialiasing soften it - this task's own complaint),
        # in `text` rather than grid_line/bevel_shadow: those two both
        # fail contrast against field_bg in at least one theme (near-
        # invisible bevel_shadow-on-field_bg in Night AND literally
        # IDENTICAL in High Contrast) - `text` is guaranteed readable
        # against field_bg in every theme, by definition of what that
        # token pairing is FOR.
        if not is_top_level:
            parent_item = item.parent()
            is_last = parent_item.indexOfChild(item) == parent_item.childCount() - 1
            pen = QPen(QColor(colors["text"]))
            pen.setWidth(1)
            pen.setStyle(Qt.PenStyle.CustomDashLine)
            pen.setDashPattern([1, 1])
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            painter.setPen(pen)
            line_x = rect.left() + _INDENT // 2
            v_bottom = rect.center().y() if is_last else rect.bottom()
            painter.drawLine(line_x, rect.top(), line_x, v_bottom)
            painter.drawLine(line_x, rect.center().y(), rect.left() + _INDENT - 2, rect.center().y())

        # --- [+]/[-] toggle box - only a top-level GROUP has one; a
        # collapsed single-page group (rendered as a bare leaf by
        # nav_model.build_nav_tree()) has none, same as any child leaf,
        # but still reserves the same column so every top-level row's
        # icon/text lines up regardless.
        icon_x = rect.left() + (_INDENT if not is_top_level else _LEFT_MARGIN)
        if is_group:
            box_rect = QRect(rect.left() + _LEFT_MARGIN, rect.center().y() - TOGGLE_SIZE // 2,
                              TOGGLE_SIZE, TOGGLE_SIZE)
            self._paint_toggle_box(painter, box_rect, item.isExpanded(), colors)
            icon_x = rect.left() + _INDENT
        elif is_top_level:
            icon_x = rect.left() + _INDENT

        text_x = icon_x + ICON_SIZE + _TEXT_GAP

        # --- attention marker (Task, prior pass: "grupa ma to
        # sygnalizowac NAWET GDY JEST ZWINIETA") - unchanged behavior,
        # just repositioned for the new icon column.
        attention = item.data(0, _ATTENTION_ROLE)
        marker_rect = None
        if attention:
            marker_color = QColor(colors["state_alarm"] if attention == ATTENTION_ALARM else colors["state_warning"])
            marker_size = 8
            marker_rect = QRect(text_x, rect.center().y() - marker_size // 2, marker_size, marker_size)
            text_x = marker_rect.right() + _TEXT_GAP

        # --- selection band (Task 6: "niebieski prostokat... obejmujacy
        # TYLKO szerokosc tekstu plus ikona - nie cala szerokosc panelu")
        # - sized to the icon+marker+text run alone via font metrics,
        # painted BEFORE the icon/marker/text themselves so those still
        # render in their own colors on top of it, exactly like
        # Explorer's own selection (the folder icon doesn't turn blue,
        # only the band behind the label does).
        text = item.text(0)
        fm = painter.fontMetrics()
        text_w = fm.horizontalAdvance(text)
        content_right = text_x + text_w + 2
        if selected:
            band = QRect(icon_x - 2, rect.top(), content_right - (icon_x - 2), rect.height())
            painter.fillRect(band, QColor(colors["accent_bg"]))
            fg = QColor(colors["accent_text"])
        else:
            fg = QColor(colors["text"])

        # --- icon (Task 3: "kazdy wezel ma mala ikone: folder dla
        # grupy, dokument dla pozycji") -------------------------------
        icon_rect = QRect(icon_x, rect.center().y() - ICON_SIZE // 2, ICON_SIZE, ICON_SIZE)
        if is_group:
            self._paint_folder_icon(painter, icon_rect, item.isExpanded(), colors)
        else:
            self._paint_page_icon(painter, icon_rect, colors)

        if marker_rect is not None:
            painter.fillRect(marker_rect, marker_color)
            painter.setPen(QColor(colors["bevel_shadow"]))
            painter.drawRect(marker_rect)

        # --- text ---
        painter.setPen(fg)
        text_rect = QRect(text_x, rect.top(), max(0, rect.right() - text_x), rect.height())
        painter.drawText(text_rect, int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft), text)
        painter.restore()

    def _paint_toggle_box(self, painter, rect, expanded, colors):
        """Task 5: "male kwadraty z ramka i wyraznym znakiem plus albo
        minus w srodku - dokladnie jak w Eksploratorze". Same raised-
        bevel look as before (bevel_light/bevel_shadow, panel_bg fill,
        so it still reads as a real button rather than part of the row
        behind it) - the previous pass already matched this
        requirement, only the box's own size shrank to fit the tighter
        row (Task 2)."""
        painter.fillRect(rect, QColor(colors["panel_bg"]))
        painter.setPen(QColor(colors["bevel_light"]))
        painter.drawLine(rect.topLeft(), rect.topRight())
        painter.drawLine(rect.topLeft(), rect.bottomLeft())
        painter.setPen(QColor(colors["bevel_shadow"]))
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())
        painter.drawLine(rect.topRight(), rect.bottomRight())
        pen = QPen(QColor(colors["text"]))
        pen.setWidth(1)
        painter.setPen(pen)
        cx, cy = rect.center().x(), rect.center().y()
        half = max(2, rect.width() // 2 - 3)
        painter.drawLine(cx - half, cy, cx + half, cy)
        if not expanded:
            painter.drawLine(cx, cy - half, cx, cy + half)

    def _paint_folder_icon(self, painter, rect, expanded, colors):
        """Task 3: a simple, era-style folder glyph - filled with
        `state_caution` (a warm amber/orange in every one of the 5
        themes, see themes.py - reads as the classic manila-folder hue
        everywhere, including the dark themes, without hardcoding a
        literal color GRANICE forbids), outlined in `text` for
        guaranteed per-theme contrast. Closed vs. expanded differ by
        whether the front flap is drawn "shut" (a plain filled body) or
        "open" (a lighter, slightly larger front flap overlapping the
        body) - simple enough to read clearly at 16px, not a pixel-
        exact Explorer icon (Task: "proste ikony... w stylu epoki")."""
        body = QColor(colors["state_caution"])
        outline = QColor(colors["text"])
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
        painter.setPen(QPen(outline, 1))
        tab = QRect(x + 1, y + 1, w * 3 // 5, 3)
        painter.setBrush(body)
        painter.drawRect(tab)
        if expanded:
            back = QRect(x + 1, y + 3, w - 3, h - 5)
            painter.setBrush(body.darker(110))
            painter.drawRect(back)
            flap = QRect(x, y + h - 7, w - 1, 6)
            painter.setBrush(body.lighter(125))
            painter.drawRect(flap)
        else:
            body_rect = QRect(x + 1, y + 3, w - 2, h - 4)
            painter.setBrush(body)
            painter.drawRect(body_rect)
        painter.setBrush(Qt.BrushStyle.NoBrush)

    def _paint_page_icon(self, painter, rect, colors):
        """Task 3: a generic small blank-document glyph (a folded top-
        right corner + a couple of text-line strokes) for a leaf page -
        the same basic shape Explorer used for a plain/unassociated
        file, simplified for 16px."""
        outline = QColor(colors["text"])
        page = QColor(colors["field_bg"])
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
        fold = 4
        poly = QPolygon([
            QPoint(x + 2, y + 1), QPoint(x + w - 2 - fold, y + 1),
            QPoint(x + w - 2, y + 1 + fold), QPoint(x + w - 2, y + h - 1),
            QPoint(x + 2, y + h - 1),
        ])
        painter.setPen(QPen(outline, 1))
        painter.setBrush(page)
        painter.drawPolygon(poly)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawLine(x + w - 2 - fold, y + 1, x + w - 2 - fold, y + 1 + fold)
        painter.drawLine(x + w - 2 - fold, y + 1 + fold, x + w - 2, y + 1 + fold)
        line_pen = QPen(QColor(colors["grid_line"]))
        line_pen.setWidth(1)
        painter.setPen(line_pen)
        ly = y + 1 + fold + 3
        while ly < y + h - 2:
            painter.drawLine(x + 3, ly, x + w - 4, ly)
            ly += 3


class NavTreeWidget(QTreeWidget):
    """Emits `page_requested(str)` with a page id whenever a click
    should switch the stacked widget - a leaf click, or a click on a
    group's own name (Task 3 of the original tree task: "kliknieciem w
    NAZWE GRUPY otwiera pierwsza dostepna strone... a nie tylko
    rozwija"). Clicking the [+]/[-] box only ever expands/collapses -
    handled entirely in mousePressEvent() below, before Qt's own
    click/selection handling ever runs, so it never ALSO navigates."""
    page_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("NavTree")
        self.setHeaderHidden(True)
        self.setRootIsDecorated(False)  # native branch triangles off - NavTreeDelegate paints its own
        self.setIndentation(0)  # ditto - the delegate positions everything itself
        self.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self.setUniformRowHeights(True)
        self.setItemDelegate(NavTreeDelegate(self))
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # matches the old flat QPushButton list - no visible focus rect
        self.setFrameShape(self.Shape.NoFrame)
        self._page_items = {}  # page_id -> QTreeWidgetItem, for set_current_page()/set_leaf_attention()
        self._suppress_expand_persist = False
        get_theme_manager().theme_changed.connect(self.viewport().update)

    # --- population -----------------------------------------------------

    def populate(self, enabled_features: dict):
        """(Re)builds the whole tree from nav_model.build_nav_tree().
        Called once at construction and again only when the feature
        configuration itself changes (a page/group appearing or
        disappearing) - NOT on every selection change, which never
        touches the tree's shape at all."""
        self.clear()
        self._page_items = {}
        expanded_state = window_state.load_nav_tree_expanded()
        nodes = build_nav_tree(enabled_features)
        for node in nodes:
            if node.kind == "leaf":
                item = QTreeWidgetItem([_display_case(tr(node.title_key))])
                item.setData(0, _PAGE_ID_ROLE, node.page_id)
                self.addTopLevelItem(item)
                self._page_items[node.page_id] = item
            else:
                group_item = QTreeWidgetItem([_display_case(tr(node.title_key))])
                group_item.setData(0, _GROUP_ID_ROLE, node.id)
                self.addTopLevelItem(group_item)
                for child in node.children:
                    child_item = QTreeWidgetItem([_display_case(tr(child.title_key))])
                    child_item.setData(0, _PAGE_ID_ROLE, child.page_id)
                    group_item.addChild(child_item)
                    self._page_items[child.page_id] = child_item
                # Task 3 (original tree task): "stan rozwiniecia
                # zapamietywany miedzy uruchomieniami" - an id never
                # seen before (first-ever run, or a group added by a
                # later version) defaults to expanded, so nothing
                # starts mysteriously collapsed.
                group_item.setExpanded(expanded_state.get(node.id, True))

    # --- selection / navigation ------------------------------------------

    def set_current_page(self, page_id: str):
        """Selects (and, if needed, expands its parent to reveal) the
        item for `page_id` - called after MainWindow switches the
        stacked widget by any OTHER means (a status-bar shortcut, a
        deny-then-elsewhere flow) so the tree's own highlight never
        drifts out of sync with what's actually on screen."""
        item = self._page_items.get(page_id)
        if item is None:
            return
        parent = item.parent()
        if parent is not None and not parent.isExpanded():
            parent.setExpanded(True)
        self.setCurrentItem(item)

    def set_leaf_attention(self, page_id: str, level):
        """Task (original tree task): "grupa ma to sygnalizowac NAWET
        GDY JEST ZWINIETA" - sets `page_id`'s own marker, then
        recomputes its parent GROUP's marker as the most severe among
        all its children (alarm beats warning beats none), so a
        collapsed group still shows the worst thing happening inside
        it. `level` is one of ATTENTION_NONE/ATTENTION_WARNING/
        ATTENTION_ALARM."""
        item = self._page_items.get(page_id)
        if item is None:
            return
        item.setData(0, _ATTENTION_ROLE, level)
        parent = item.parent()
        if parent is not None:
            worst = ATTENTION_NONE
            for i in range(parent.childCount()):
                child_level = parent.child(i).data(0, _ATTENTION_ROLE)
                if child_level == ATTENTION_ALARM:
                    worst = ATTENTION_ALARM
                    break
                if child_level == ATTENTION_WARNING and worst != ATTENTION_ALARM:
                    worst = ATTENTION_WARNING
            parent.setData(0, _ATTENTION_ROLE, worst)
        self.viewport().update()

    # --- input ------------------------------------------------------------

    def mousePressEvent(self, event):
        index = self.indexAt(event.pos())
        if not index.isValid():
            return super().mousePressEvent(event)
        item = self.itemFromIndex(index)
        is_top_level = not index.parent().isValid()
        if is_top_level and item.childCount() > 0:
            # Task 2's touch compromise: the drawn [+]/[-] glyph is only
            # TOGGLE_SIZE (13px) so the tree can look authentically
            # tight, but the actual tap target here is the WHOLE
            # toggle/connector column (_INDENT=22px wide, the full
            # ROW_HEIGHT=24px tall) at a fixed, predictable position -
            # a finger doesn't have to land on the small square itself,
            # only somewhere in its column. A miss past this column
            # falls through to "click the group's name" below, which
            # still navigates somewhere useful (never a no-op, never a
            # wrong control action) - see SESSION_REPORT.md.
            row_rect = self.visualRect(index)
            hit_rect = QRect(row_rect.left(), row_rect.top(), _INDENT, row_rect.height())
            if hit_rect.contains(event.pos()):
                item.setExpanded(not item.isExpanded())
                self._persist_expansion()
                return  # box-column click ONLY toggles - never navigates
        super().mousePressEvent(event)
        page_id = item.data(0, _PAGE_ID_ROLE)
        if page_id is None and item.childCount() > 0:
            # A click on a group's own name/row (not its box, handled
            # above) - Task (original tree task): "otwiera pierwsza
            # dostepna strone z tej grupy, a nie tylko rozwija".
            page_id = item.child(0).data(0, _PAGE_ID_ROLE)
        if page_id is not None:
            self.page_requested.emit(page_id)

    def _persist_expansion(self):
        if self._suppress_expand_persist:
            return
        state = {}
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            group_id = item.data(0, _GROUP_ID_ROLE)
            if group_id is not None:
                state[group_id] = item.isExpanded()
        window_state.save_nav_tree_expanded(state)
