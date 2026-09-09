"""On-screen touch keyboard - a transparent input layer, not a form
change. Nothing in any page/dialog needs to know this exists: a single
application-wide event filter (OnScreenKeyboardController, installed
once from main_window.py) watches every QLineEdit/QAbstractSpinBox in
the whole app for focus, and if the on-screen keyboard is enabled, pops
up the right kind of keyboard and edits the field through its own normal
QLineEdit API (insert()/backspace()/clear()) - the exact same calls a
physical keyboard's key events end up making internally, so every
field's own validators/maxLength/textChanged handlers fire exactly as
they always did. No page or dialog file imports anything from this
module.

Deliberately hand-built (QWidget + QPushButton grids), not Qt Virtual
Keyboard (`PySide6-Addons`' QtVirtualKeyboard / qml module): the
open-source edition of Qt Virtual Keyboard is GPL-licensed, which would
undo the point of the PyQt6 (GPL/commercial) -> PySide6 (LGPL) migration
this codebase just went through. See SESSION_REPORT.md for this decision
recorded as its own item, not just a code comment.

Each keyboard is a real floating, draggable, resizable top-level window
(own title bar with a close button, QSizeGrip in the corner) - NOT a bar
docked to the target's window, which is what the previous design did and
is exactly what caused this task's Part 1 bug: docking sized the
keyboard to the target window's own width/position, so for a small
popup like the PIN dialog the keyboard ended up positioned exactly on
top of (and taller than) that popup, fully hiding it underneath an
always-on-top window - see SESSION_REPORT.md for the geometry proof.
Position/size are remembered between runs (window_state.py, same
pattern as the main window's own geometry), and the keyboard now STAYS
open across field switches - only a manual close (the window's own X,
or turning the Settings toggle off) hides it; confirming/cancelling a
field's edit no longer auto-hides it.

Two keyboards:
  - NumericKeypad: 0-9, Backspace, Clear, OK, Cancel. Used for PIN
    fields and any QAbstractSpinBox (QSpinBox/QDoubleSpinBox) - numeric
    ranges/decimals/PIN entry all round-trip through digits only.
  - FullKeyboard: QWERTY + digits row + space/backspace/Shift + OK/
    Cancel, for every other (non-read-only) QLineEdit - descriptions,
    tag names, technical notes, search boxes. Polish diacritical
    letters (ą ć ę ł ń ó ś ź ż) are reachable by long-pressing (or a
    slow click-and-hold via mouse, for a mouse-driven dev machine) the
    base Latin letter, instead of a 9th keyboard row - keeps the layout
    to the same size as a plain QWERTY board.
"""

from PySide6.QtWidgets import (
    QWidget, QPushButton, QGridLayout, QVBoxLayout, QHBoxLayout,
    QLineEdit, QAbstractSpinBox, QLabel, QSizeGrip, QSizePolicy, QApplication,
)
from PySide6.QtCore import Qt, QEvent, QObject, QTimer, Signal, QRect, QPoint
from PySide6.QtGui import QGuiApplication

from epw_os.i18n import tr
from epw_os.gui import window_state

# Held-down duration (ms) before a long-press reveals the accented
# variant of a letter, instead of typing the plain one immediately.
_LONG_PRESS_MS = 450

_DIACRITICS = {
    "a": "ą", "c": "ć", "e": "ę", "l": "ł", "n": "ń",
    "o": "ó", "s": "ś", "z": "ź",  # "z" long-press cycles z -> ż below
}
_DIACRITICS_SHIFT = {k.upper(): v.upper() for k, v in _DIACRITICS.items()}
# "z"/"Z" has two accented forms (ź and ż) - long-press cycles between
# them instead of picking just one, so neither is unreachable.
_Z_VARIANTS = ["z", "ź", "ż"]
_Z_VARIANTS_UPPER = ["Z", "Ź", "Ż"]

# ~10mm in device pixels - the smallest a key may shrink to while the
# keyboard window itself is resized down, so a finger can still reliably
# hit one. Computed lazily (needs a QApplication/screen to exist) and
# cached; falls back to a plain 38px (close to 10mm at a typical 96 DPI)
# if no screen is available at all (e.g. some offscreen test setups).
_min_key_px_cache = None


def _min_key_px() -> int:
    global _min_key_px_cache
    if _min_key_px_cache is not None:
        return _min_key_px_cache
    screen = QGuiApplication.primaryScreen()
    dpi = screen.logicalDotsPerInch() if screen is not None else 96.0
    _min_key_px_cache = max(int(round(10.0 / 25.4 * dpi)), 28)
    return _min_key_px_cache


def _effective_line_edit(widget):
    """The QLineEdit that actually holds the text being typed into -
    widget itself for a QLineEdit, or its internal editor for a spin
    box. None for anything else (caller should not have gotten here)."""
    if isinstance(widget, QAbstractSpinBox):
        return widget.lineEdit()
    if isinstance(widget, QLineEdit):
        return widget
    return None


class _KeyButton(QPushButton):
    """A keyboard key. Plain click types `base`. If `alt` is given, a
    long press (or a long-press cycling through `alt` when it's a list,
    for the ź/ż case) types the accented variant instead.

    Expanding size policy (not a fixed pixel size) with only a minimum
    enforced (~10mm, see _min_key_px()) - this is what lets the whole
    keyboard scale with its window instead of leaving dead space around
    fixed-size buttons (Part 2 of the task)."""

    character_typed = Signal(str)

    def __init__(self, base, alt=None, parent=None):
        super().__init__(base, parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(_min_key_px(), _min_key_px())
        # Never take keyboard focus on click - a QPushButton's default
        # focus policy would otherwise pull focus away from whatever
        # field is being typed into (a modal PIN dialog reacts to that
        # by closing itself - see SESSION_REPORT.md for this task).
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._base = base
        self._alt_sequence = alt if isinstance(alt, (list, tuple)) else ([alt] if alt else [])
        self._alt_index = 0
        self._fired_alt = False
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._emit_alt)
        self.pressed.connect(self._on_pressed)
        self.released.connect(self._on_released)

    def _on_pressed(self):
        self._fired_alt = False
        if self._alt_sequence:
            self._timer.start(_LONG_PRESS_MS)

    def _emit_alt(self):
        self._fired_alt = True
        ch = self._alt_sequence[self._alt_index % len(self._alt_sequence)]
        self._alt_index += 1
        self.character_typed.emit(ch)

    def _on_released(self):
        if self._timer.isActive():
            self._timer.stop()
        if not self._fired_alt:
            self.character_typed.emit(self._base)


def _expanding(btn: QPushButton, min_px: int = None):
    """Apply the same Expanding-with-a-floor policy as _KeyButton to a
    plain QPushButton (Backspace/Clear/Shift/Space/punctuation/OK/
    Cancel) so the whole keyboard scales together, not just the letter
    keys. Also NoFocus, for the same reason as _KeyButton above."""
    btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    btn.setMinimumSize(min_px or _min_key_px(), _min_key_px())
    btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    return btn


class _TitleBar(QWidget):
    """Draggable title strip + close button - the window has no native
    OS frame (FramelessWindowHint), so dragging/closing has to be
    hand-rolled, same as any other borderless floating tool window."""

    def __init__(self, window: "QWidget"):
        super().__init__()
        self._window = window
        self._drag_offset = None
        self.setObjectName("OnScreenKeyboardTitleBar")
        self.setFixedHeight(26)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setStyleSheet(
            "QWidget#OnScreenKeyboardTitleBar { background-color: #000080; }"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 2, 0)
        lbl = QLabel(tr("keyboard.window_title"))
        lbl.setStyleSheet("color: white; font-weight: bold; background: transparent;")
        layout.addWidget(lbl)
        layout.addStretch()

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(22, 22)
        btn_close.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn_close.setStyleSheet(
            "QPushButton { background: transparent; color: white; border: none; font-weight: bold; }"
            "QPushButton:hover { background-color: #AA0000; }"
        )
        btn_close.setToolTip(tr("keyboard.close"))
        btn_close.clicked.connect(window.hide)
        layout.addWidget(btn_close)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self._window.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None and (event.buttons() & Qt.MouseButton.LeftButton):
            self._window.move(event.globalPosition().toPoint() - self._drag_offset)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_offset = None
        self._window._persist_geometry()
        super().mouseReleaseEvent(event)


class _BaseKeyboard(QWidget):
    """Shared plumbing: a real floating window (title bar, close button,
    resize grip), attach to a target field, capture/restore text,
    reposition itself only if it would otherwise cover the field being
    edited, and persist its own position/size between runs."""

    def __init__(self):
        super().__init__(
            None,
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus,
        )
        # Belt and suspenders against stealing focus from whatever field
        # is actually being edited (a modal dialog - e.g. the PIN prompt,
        # Change PIN, any confirmation popup, the Historian export
        # dialog - reacts to losing its own focus by closing itself):
        # WindowDoesNotAcceptFocus above stops the *window* from ever
        # becoming active; WA_ShowWithoutActivating stops show()/raise_()
        # from activating it either; NoFocus on every button below (see
        # _KeyButton/_expanding/_TitleBar) stops Qt's own internal
        # focus-widget tracking from moving focus there on click. All
        # three together, not just one - see SESSION_REPORT.md for why
        # this needed a real fix, not a partial one.
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setObjectName("OnScreenKeyboard")
        self.setStyleSheet(
            "QWidget#OnScreenKeyboard { background-color: #D4D0C8; border: 2px solid #000080; }"
        )
        self._target = None
        self._original_text = ""
        self._restoring_geometry = False

        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(0, 0, 0, 0)
        self._outer.setSpacing(0)
        self._outer.addWidget(_TitleBar(self))

        self._content = QVBoxLayout()
        self._content.setContentsMargins(8, 8, 8, 4)
        self._content.setSpacing(4)
        self._outer.addLayout(self._content, stretch=1)

        grip_row = QHBoxLayout()
        grip_row.setContentsMargins(0, 0, 2, 2)
        grip_row.addStretch()
        size_grip = QSizeGrip(self)
        size_grip.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        grip_row.addWidget(size_grip)
        self._outer.addLayout(grip_row)

        self._apply_initial_geometry()

    # --- geometry: restore/persist across runs, avoid covering fields --

    def _apply_initial_geometry(self):
        geo = window_state.load_keyboard_geometry()
        self.resize(geo["width"], geo["height"])
        if geo["x"] is not None and geo["y"] is not None:
            self.move(geo["x"], geo["y"])
        else:
            self._move_to_default_position()

    def _move_to_default_position(self):
        screen = QGuiApplication.primaryScreen()
        avail = screen.availableGeometry() if screen is not None else QRect(0, 0, 1024, 768)
        self.move(
            max(avail.left(), avail.right() - self.width() - 20),
            max(avail.top(), avail.bottom() - self.height() - 20),
        )

    def _persist_geometry(self):
        if self._restoring_geometry:
            return
        g = self.geometry()
        window_state.save_keyboard_geometry(g.x(), g.y(), g.width(), g.height())

    def moveEvent(self, event):
        super().moveEvent(event)
        self._persist_geometry()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._persist_geometry()

    def _reposition_if_covering(self, target):
        """Only moves the window if it would otherwise hide the field
        being edited - an already-clear position (wherever the operator
        last left it) is never disturbed."""
        field_global = QRect(target.mapToGlobal(QPoint(0, 0)), target.size())
        kb_rect = self.frameGeometry()
        if not kb_rect.intersects(field_global):
            return

        screen = target.screen() if hasattr(target, "screen") and target.screen() else QGuiApplication.primaryScreen()
        avail = screen.availableGeometry() if screen is not None else QRect(0, 0, 1024, 768)

        new_y = field_global.bottom() + 8
        if new_y + kb_rect.height() > avail.bottom():
            new_y = field_global.top() - kb_rect.height() - 8
        new_y = max(avail.top(), min(new_y, avail.bottom() - kb_rect.height()))

        new_x = min(max(kb_rect.x(), avail.left()), avail.right() - kb_rect.width())

        self._restoring_geometry = True  # this move is automatic, not a
        # deliberate drag - still worth remembering for next time, but
        # doesn't need the extra write countable as "the operator moved
        # it"; kept simple by just persisting once at the end instead.
        self.move(new_x, new_y)
        self._restoring_geometry = False
        self._persist_geometry()

    # --- attach/detach ---------------------------------------------------

    def attach(self, target):
        editor = _effective_line_edit(target)
        if editor is None:
            return
        self._target = editor
        self._original_text = editor.text()
        self._reposition_if_covering(target)
        self.show()
        self.raise_()

    def _type(self, ch):
        if self._target is not None:
            self._target.insert(ch)

    def _backspace(self):
        if self._target is not None:
            self._target.backspace()

    def _clear(self):
        if self._target is not None:
            self._target.clear()

    def _confirm(self):
        """Keep the typed text and detach from this field - the keyboard
        window itself stays open (Part 2 of the task), ready for
        whichever field is focused next. Only a manual close (the
        window's own X, or the Settings toggle) actually hides it."""
        self._target = None

    def _cancel(self):
        if self._target is not None:
            self._target.setText(self._original_text)
        self._target = None


class NumericKeypad(_BaseKeyboard):
    """0-9 + Backspace + Clear + OK + Cancel - PIN fields and any
    QAbstractSpinBox (ranges, decimals)."""

    def __init__(self):
        super().__init__()

        grid = QGridLayout()
        grid.setSpacing(4)
        positions = [
            ("7", 0, 0), ("8", 0, 1), ("9", 0, 2),
            ("4", 1, 0), ("5", 1, 1), ("6", 1, 2),
            ("1", 2, 0), ("2", 2, 1), ("3", 2, 2),
            ("0", 3, 0),
        ]
        for digit, row, col in positions:
            btn = _KeyButton(digit)
            btn.character_typed.connect(self._type)
            grid.addWidget(btn, row, col)

        btn_back = _expanding(QPushButton("←"))
        btn_back.clicked.connect(self._backspace)
        grid.addWidget(btn_back, 3, 1)

        btn_clear = _expanding(QPushButton("C"))
        btn_clear.clicked.connect(self._clear)
        grid.addWidget(btn_clear, 3, 2)

        self._content.addLayout(grid, stretch=1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)
        self.btn_cancel = _expanding(QPushButton(tr("keyboard.cancel")))
        self.btn_ok = _expanding(QPushButton(tr("keyboard.ok")))
        self.btn_cancel.clicked.connect(self._cancel)
        self.btn_ok.clicked.connect(self._confirm)
        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_ok)
        self._content.addLayout(btn_row)

        # 3 columns wide, 5 rows tall (digits x4 + OK/Cancel row) is the
        # densest this keyboard gets - the floor for "still resizable
        # down to a usable size" (Part 2's ~10mm-per-key requirement).
        min_px = _min_key_px()
        self.setMinimumSize(min_px * 3 + 40, min_px * 5 + 60)


class FullKeyboard(_BaseKeyboard):
    """QWERTY + digits row + space/backspace/Shift + OK/Cancel - every
    other editable QLineEdit (descriptions, tag names, technical notes,
    search boxes). Polish diacritics reachable by long-pressing the
    base letter (a/c/e/l/n/o/s/z), not a dedicated row - see the module
    docstring."""

    _ROWS = [
        "1234567890",
        "qwertyuiop",
        "asdfghjkl",
        "zxcvbnm",
    ]

    def __init__(self):
        super().__init__()
        self._shift = False
        self._letter_buttons = []  # (button, base_lower) for shift re-labeling

        for row_chars in self._ROWS:
            row = QHBoxLayout()
            row.setSpacing(3)
            for ch in row_chars:
                alt = _Z_VARIANTS[1:] if ch == "z" else _DIACRITICS.get(ch)
                btn = _KeyButton(ch, alt)
                btn.character_typed.connect(self._type_respecting_shift)
                row.addWidget(btn)
                if ch.isalpha():
                    self._letter_buttons.append(btn)
            self._content.addLayout(row)

        bottom = QHBoxLayout()
        bottom.setSpacing(3)

        self.btn_shift = _expanding(QPushButton(tr("keyboard.shift")))
        self.btn_shift.setCheckable(True)
        self.btn_shift.toggled.connect(self._on_shift_toggled)
        bottom.addWidget(self.btn_shift)

        btn_space = QPushButton(tr("keyboard.space"))
        # Bug fix: this button used to get the same tiny per-key square
        # minimum every other key gets (_min_key_px(), sized for a single
        # character) - fine for "C"/"<-"/a letter, not for a multi-
        # character label like "Space"/"Spacja". A QPushButton's text is
        # center-aligned and Qt does not auto-elide it, so a button
        # narrower than its own label just shows the middle slice of the
        # text (reported: "pac" instead of "Space"). Floor this button's
        # own minimum width at whatever its actual label needs, so it
        # always fits - at every keyboard size, in either language -
        # instead of relying on the stretch factor below happening to
        # give it enough room.
        space_min_w = max(_min_key_px(), btn_space.fontMetrics().horizontalAdvance(btn_space.text()) + 24)
        _expanding(btn_space, min_px=space_min_w)
        btn_space.clicked.connect(lambda: self._type(" "))
        bottom.addWidget(btn_space, stretch=3)

        for ch in (".", "-", "_"):
            btn = _expanding(QPushButton(ch))
            btn.clicked.connect(lambda checked=False, c=ch: self._type(c))
            bottom.addWidget(btn)

        btn_back = _expanding(QPushButton("←"))
        btn_back.clicked.connect(self._backspace)
        bottom.addWidget(btn_back)

        self._content.addLayout(bottom)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)
        self.btn_cancel = _expanding(QPushButton(tr("keyboard.cancel")))
        self.btn_ok = _expanding(QPushButton(tr("keyboard.ok")))
        self.btn_cancel.clicked.connect(self._cancel)
        self.btn_ok.clicked.connect(self._confirm)
        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_ok)
        self._content.addLayout(btn_row)

        # 10 columns wide (the digits/qwertyuiop rows), 6 rows tall
        # (4 letter rows + bottom row + OK/Cancel row).
        min_px = _min_key_px()
        self.setMinimumSize(min_px * 10 + 60, min_px * 6 + 70)

    def attach(self, target):
        self.btn_shift.setChecked(False)  # every field starts lowercase
        super().attach(target)

    def _on_shift_toggled(self, checked):
        self._shift = checked
        for btn in self._letter_buttons:
            btn.setText(btn._base.upper() if checked else btn._base.lower())

    def _type_respecting_shift(self, ch):
        # Long-press already returns the exact accented character to
        # type (lower or upper, chosen by _DIACRITICS/_DIACRITICS_SHIFT
        # below); a plain-letter tap from _KeyButton is always lowercase
        # and needs Shift applied here.
        if len(ch) == 1 and ch.isalpha() and ch.islower() and self._shift:
            ch = _DIACRITICS_SHIFT.get(ch.upper(), ch.upper())
        self._type(ch)
        # Shift is not sticky (matches a real on-screen keyboard/phone
        # keyboard convention) - one capital per tap, then back to lower.
        if self._shift:
            self.btn_shift.setChecked(False)


class EmbeddedNumericKeypad(QWidget):
    """A numeric keypad as a plain CHILD widget inside a dialog's own
    layout - NOT a separate floating top-level window like NumericKeypad
    above. Built for modal dialogs with a masked PIN field
    (PinPromptPopup, Settings' Change PIN).

    Why this exists (see SESSION_REPORT.md for the full writeup): fixing
    Bug 1 (PinPromptPopup closing itself on any outside click) by
    switching it from Qt.WindowType.Popup to Qt.WindowType.Dialog
    surfaced a DIFFERENT, deeper problem, confirmed on real hardware -
    clicking a digit on the floating NumericKeypad stopped reaching the
    field at all. Root cause: Qt::ApplicationModal (what .exec() gives a
    plain Dialog) blocks input delivery to every top-level window OUTSIDE
    the modal dialog's own widget hierarchy - and the floating keyboard
    is exactly such an outside window. Two attempts at patching that
    cross-window communication failed. This widget removes the
    cross-window step entirely: as a child of the same dialog, there is
    no separate window for Qt to block in the first place.

    No title bar, resize grip, or OK/Cancel here (unlike NumericKeypad) -
    this lives inside a dialog that already has its own Unlock/Cancel or
    Save/Close buttons, so a second pair would be redundant. attach()
    lets one instance serve several fields in the same dialog (Change
    PIN's old/new/confirm), retargeted by the caller's own focus
    tracking - see PinChangeSection.eventFilter()."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._target = None

        grid = QGridLayout(self)
        grid.setSpacing(4)
        positions = [
            ("7", 0, 0), ("8", 0, 1), ("9", 0, 2),
            ("4", 1, 0), ("5", 1, 1), ("6", 1, 2),
            ("1", 2, 0), ("2", 2, 1), ("3", 2, 2),
            ("0", 3, 0),
        ]
        for digit, row, col in positions:
            btn = _KeyButton(digit)
            btn.character_typed.connect(self._type)
            grid.addWidget(btn, row, col)

        btn_back = _expanding(QPushButton("←"))
        btn_back.clicked.connect(self._backspace)
        grid.addWidget(btn_back, 3, 1)

        btn_clear = _expanding(QPushButton("C"))
        btn_clear.clicked.connect(self._clear)
        grid.addWidget(btn_clear, 3, 2)

        # Same ~10mm-per-key touch-target floor as every other keyboard in
        # this module (_min_key_px()) - a dialog embedding this widget
        # should size itself around it, not shrink it below usability.
        min_px = _min_key_px()
        self.setMinimumSize(min_px * 3 + 16, min_px * 4 + 16)

    def attach(self, field):
        self._target = field

    def _type(self, ch):
        if self._target is not None:
            self._target.insert(ch)

    def _backspace(self):
        if self._target is not None:
            self._target.backspace()

    def _clear(self):
        if self._target is not None:
            self._target.clear()


# Dynamic Qt property name used to flag a field as already having its own
# EmbeddedNumericKeypad (see mark_embedded_keypad_field() and its use in
# _maybe_show_for() below) - a plain module-level string constant would
# work identically, this is just the one Qt already gives every QObject
# for exactly this kind of "attach arbitrary metadata to a widget" need.
_EMBEDDED_KEYPAD_PROPERTY = "epw_embedded_numeric_keypad"


def mark_embedded_keypad_field(field):
    """Call on a QLineEdit that already has its own EmbeddedNumericKeypad
    built directly into its dialog (PinPromptPopup, PinChangeSection) -
    stops OnScreenKeyboardController below from ALSO trying to attach a
    second, separate floating keypad to the same field. Without this, an
    operator with the on-screen keyboard enabled would see two competing
    numeric keypads for one field - and the floating one would be the
    broken one again (see EmbeddedNumericKeypad's docstring)."""
    field.setProperty(_EMBEDDED_KEYPAD_PROPERTY, True)


class OnScreenKeyboardController(QObject):
    """Installed once, application-wide (see MainWindow.__init__), as an
    event filter on QApplication. Shows the right keyboard whenever a
    matching field gains focus, if enabled. `is_enabled` is a zero-arg
    callable rather than a plain bool so the caller (MainWindow) can
    flip the Settings toggle live without reinstalling anything."""

    def __init__(self, is_enabled, parent=None):
        super().__init__(parent)
        self.is_enabled = is_enabled
        self._numeric = NumericKeypad()
        self._full = FullKeyboard()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.FocusIn and self.is_enabled():
            self._maybe_show_for(obj)
        return False  # never consume - this is purely observational

    def _maybe_show_for(self, obj):
        if obj.property(_EMBEDDED_KEYPAD_PROPERTY):
            # This field already has its own EmbeddedNumericKeypad built
            # directly into its dialog (see mark_embedded_keypad_field())
            # - PinPromptPopup and Settings' Change PIN do this instead of
            # relying on this floating, separate-window keyboard, since a
            # modal dialog blocks input to any top-level window outside
            # its own hierarchy (see SESSION_REPORT.md).
            return
        if isinstance(obj, QAbstractSpinBox):
            self._numeric.attach(obj)
            return
        if isinstance(obj, QLineEdit):
            if obj.isReadOnly():
                return  # e.g. an existing Analog point's locked Tag field
            if obj.echoMode() == QLineEdit.EchoMode.Password:
                self._numeric.attach(obj)
            else:
                self._full.attach(obj)

    def hide_all(self):
        """Settings > On-Screen Keyboard turned off - closing the
        feature must also close whatever keyboard window happens to be
        open right now, not just stop opening new ones."""
        self._numeric.hide()
        self._full.hide()
