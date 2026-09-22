"""feat/signal-register §2 — the "Sygnały" department.

Owner: "Waldek chce móc dodawać bity z jednego miejsca, jak rejestr
punktów." Until now a marker could only be created from inside the logic
editor - either through Project settings, or by way of the picker that
opens from a block. Both are the right door when you are already wiring
something up; neither is a place to sit down and design the signal list
of an installation, which is what the point registry is for points.

TWO TABS, TWO COMPLETELY DIFFERENT KINDS OF THING.

  * INTERNAL - this project's own markers. Editable, because they belong
    to this installation and nobody else has an opinion about them.

  * SYSTEM - the platform catalog. Read-only, because it is a CONTRACT:
    the same 42 names, with the same meanings, in every project on every
    controller. A project that could add to it would be inventing a
    signal EPW-OS has never heard of, which logic would read happily
    and which would never change value. The panel says so in as many
    words rather than just disabling the buttons.

ONE REGISTRY, NOT TWO. The markers live in the LOGIC project's own
settings["internal_bits"] and this panel edits exactly that object - it
never keeps a copy, never mirrors into projekt.epw, and reaches the
logic project through the embedded editor Studio already owns. A second
STORE of the same bits is the mistake this codebase has made before; a
second DOOR into the one store is not.

The rules that could drift between this panel and the editor's own
registry table - what counts as "used", and that a rename must re-point
every block - are not implemented here. They live in
shared/logic/internal_bits.py and both editors call them.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QMessageBox, QPushButton, QTabWidget, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from studio.shell.i18n import tr

_TYPES = ("BOOL", "REAL")


def _prep_table(table: QTableWidget):
    """The same table conventions every other department uses - no
    vertical header, whole-row selection, striped rows, and no Stretch
    mode anywhere (Qt makes a Stretch section un-draggable, which is the
    bug the other panels' own comment records)."""
    table.verticalHeader().setVisible(False)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setAlternatingRowColors(True)


def _resizable(table: QTableWidget, column: int, width: int):
    table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeMode.Interactive)
    table.setColumnWidth(column, width)


def _read_only(text: str) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    return item


class InternalSignalsTab(QWidget):
    """The project's markers: add, rename, describe, delete.

    Every edit writes straight into the logic project's registry list and
    then tells the logic editor it is dirty - the project is saved by
    whoever saves projects, exactly like any other department.
    """

    # Owner's order (2026-09-22): what a signal IS first (name, id, type,
    # retention), then where it is used, then how it is described; the
    # description last, taking whatever width is left.
    _COLS = ("name", "id", "type", "retentive", "used_by", "category", "label", "description")
    COL_NAME, COL_ID, COL_TYPE, COL_RETENTIVE, COL_USED, COL_CATEGORY, COL_LABEL, COL_DESCRIPTION = range(8)
    # Initial widths (px): together they must leave "Used in" whole in a
    # 1280 x 720 window without a horizontal scrollbar - measured with
    # tests/test_signals_panel.py's own width test.
    COLUMN_WIDTHS = {COL_NAME: 140, COL_ID: 120, COL_TYPE: 70, COL_RETENTIVE: 70,
                     COL_USED: 190, COL_CATEGORY: 110, COL_LABEL: 100}

    def __init__(self, studio_window, parent=None):
        super().__init__(parent)
        self._studio_window = studio_window
        self._loading = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        heading = QLabel(tr("signals.internal_heading"))
        heading.setObjectName("PanelHeading")
        layout.addWidget(heading)
        intro = QLabel(tr("signals.internal_intro"))
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self.table = QTableWidget(0, len(self._COLS))
        self.table.setHorizontalHeaderLabels([tr(f"signals.col_{c}") for c in self._COLS])
        _prep_table(self.table)
        for column, width in self.COLUMN_WIDTHS.items():
            _resizable(self.table, column, width)
        # The description is last and stretches over the remaining width
        # (Qt: a stretched last section is not user-resizable; every
        # other column stays Interactive - draggable).
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(self.COL_DESCRIPTION, QHeaderView.ResizeMode.Stretch)
        self.table.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.table)

        buttons = QHBoxLayout()
        self.add_button = QPushButton(tr("signals.add"))
        self.add_button.clicked.connect(self.add_signal)
        buttons.addWidget(self.add_button)
        self.delete_button = QPushButton(tr("signals.delete"))
        self.delete_button.clicked.connect(self.delete_selected)
        buttons.addWidget(self.delete_button)
        buttons.addStretch()
        layout.addLayout(buttons)

        self._unavailable = QLabel(tr("signals.logic_unavailable"))
        self._unavailable.setWordWrap(True)
        self._unavailable.setVisible(False)
        layout.addWidget(self._unavailable)

        self.refresh()

    # -- the one registry ---------------------------------------------------

    def logic_project(self):
        """The LOGIC project, whose settings hold the registry.

        Opening this department builds the embedded editor if it is not
        built yet - the registry has no other home, and a panel that
        edited a copy until the editor happened to open would be the
        second store this whole module's docstring is about.
        """
        window = self._studio_window
        ensure = getattr(window, "_ensure_logic_panel", None)
        if ensure is not None:
            try:
                ensure()
            except Exception:  # noqa: BLE001 - an editor that will not build is reported, not raised
                return None
        panel = getattr(window, "_logic_panel", None)
        if panel is None:
            return None
        return getattr(panel.main_window(), "project", None)

    def entries(self) -> list:
        project = self.logic_project()
        if project is None:
            return []
        return project.settings.setdefault("internal_bits", [])

    def _blocks(self) -> list:
        project = self.logic_project()
        return list(getattr(project, "blocks", []) or []) if project else []

    def _mark_changed(self):
        """Dirty the LOGIC project (it owns the registry) and let Studio
        re-render whatever depends on the project as a whole."""
        window = self._studio_window
        panel = getattr(window, "_logic_panel", None)
        if panel is not None:
            main_window = panel.main_window()
            if hasattr(main_window, "set_dirty"):
                main_window.set_dirty()
            refresh = getattr(main_window, "_refresh_project_dependent_panels", None)
            if refresh is not None:
                refresh()
        if hasattr(window, "_on_project_changed"):
            window._on_project_changed()

    # -- display ------------------------------------------------------------

    def refresh(self):
        from shared.logic.internal_bits import blocks_using, internal_bit_id

        project = self.logic_project()
        available = project is not None
        self._unavailable.setVisible(not available)
        self.table.setEnabled(available)
        self.add_button.setEnabled(available)
        self.delete_button.setEnabled(available)

        self._loading = True
        try:
            entries = self.entries()
            blocks = self._blocks()
            self.table.setRowCount(len(entries))
            for row, entry in enumerate(entries):
                self.table.setItem(row, self.COL_NAME, QTableWidgetItem(entry.get("name", "")))
                # The id is DERIVED from name+type+retentive, never stored -
                # showing it read-only is what makes the retention column
                # mean something visible (M. vs MR., MW. vs MWR.).
                self.table.setItem(row, self.COL_ID, _read_only(internal_bit_id(entry)))

                type_combo = QComboBox()
                type_combo.addItems(_TYPES)
                type_combo.setCurrentText(entry.get("type") if entry.get("type") in _TYPES else "BOOL")
                type_combo.currentTextChanged.connect(
                    lambda text, r=row: self._set_field(r, "type", text))
                self.table.setCellWidget(row, self.COL_TYPE, type_combo)

                retentive = QCheckBox()
                retentive.setChecked(bool(entry.get("retentive")))
                retentive.setToolTip(tr("signals.retentive_tooltip"))
                retentive.toggled.connect(
                    lambda checked, r=row: self._set_field(r, "retentive", bool(checked)))
                self.table.setCellWidget(row, self.COL_RETENTIVE, retentive)

                self.table.setItem(row, self.COL_DESCRIPTION, QTableWidgetItem(entry.get("description", "")))
                self.table.setItem(row, self.COL_CATEGORY, QTableWidgetItem(entry.get("category", "")))
                self.table.setItem(row, self.COL_LABEL, QTableWidgetItem(entry.get("label", "")))

                used = blocks_using(blocks, entry.get("name", ""))
                self.table.setItem(row, self.COL_USED, _read_only(self._used_text(used)))
        finally:
            self._loading = False

    @staticmethod
    def _used_text(used) -> str:
        if not used:
            return tr("signals.unused")
        return ", ".join(b.short_id or b.uuid[:8] for b in used)

    # -- editing ------------------------------------------------------------

    def _on_item_changed(self, item):
        if self._loading:
            return
        row, column = item.row(), item.column()
        entries = self.entries()
        if not (0 <= row < len(entries)):
            return
        text = item.text().strip()

        if column == self.COL_NAME:
            self._rename(row, text)
            return
        for col, key in ((self.COL_DESCRIPTION, "description"),
                         (self.COL_CATEGORY, "category"),
                         (self.COL_LABEL, "label")):
            if column == col:
                entries[row][key] = text
                self._mark_changed()
                return

    def _set_field(self, row: int, key: str, value):
        entries = self.entries()
        if not (0 <= row < len(entries)) or entries[row].get(key) == value:
            return
        entries[row][key] = value
        self._mark_changed()
        self.refresh()   # the derived id column changes with both of these

    def _rename(self, row: int, new_name: str):
        """A rename is the one edit that reaches outside the registry:
        every block referring to the old name has to follow it, or the
        next compile reports each of them as an unknown signal."""
        from shared.logic.internal_bits import (
            blocks_using, rename_in_blocks, validate_internal_bit_name,
        )

        entries = self.entries()
        old_name = entries[row].get("name", "")
        if new_name == old_name:
            return

        error = validate_internal_bit_name(new_name)
        if error:
            QMessageBox.warning(self, tr("signals.invalid_name"), error)
            self.refresh()
            return
        if self._name_taken(new_name, skip_row=row):
            QMessageBox.warning(self, tr("signals.duplicate_title"),
                                tr("signals.duplicate_text", name=new_name))
            self.refresh()
            return

        moved = rename_in_blocks(self._blocks(), old_name, new_name)
        entries[row]["name"] = new_name
        self._mark_changed()
        self.refresh()
        if moved:
            window = self._studio_window
            if hasattr(window, "statusBar"):
                window.statusBar().showMessage(
                    tr("signals.renamed_blocks", name=new_name, n=moved), 8000)

    def _name_taken(self, name: str, skip_row: int = -1) -> bool:
        lname = name.lower()
        return any(row != skip_row and (entry.get("name", "") or "").lower() == lname
                   for row, entry in enumerate(self.entries()))

    def add_signal(self):
        entries = self.entries()
        if self.logic_project() is None:
            return
        base = tr("signals.new_name_base")
        name, suffix = base, 1
        while self._name_taken(name):
            suffix += 1
            name = f"{base}_{suffix}"
        entries.append({
            "name": name, "type": "BOOL", "retentive": False,
            "description": "", "label": "", "category": "",
        })
        self._mark_changed()
        self.refresh()
        row = len(entries) - 1
        self.table.setCurrentCell(row, self.COL_NAME)
        self.table.editItem(self.table.item(row, self.COL_NAME))

    def delete_selected(self):
        """Deleting a marker that blocks still read or write is not
        refused - sometimes that IS the intention - but it is never
        silent: the blocks that will be left pointing at nothing are
        named, because "unknown signal" at the next compile, five
        messages down, is the wrong place to find out."""
        from shared.logic.internal_bits import blocks_using

        entries = self.entries()
        rows = sorted({index.row() for index in self.table.selectedIndexes()}, reverse=True)
        rows = [row for row in rows if 0 <= row < len(entries)]
        if not rows:
            return

        blocks = self._blocks()
        in_use = []
        for row in rows:
            used = blocks_using(blocks, entries[row].get("name", ""))
            if used:
                in_use.append((entries[row].get("name", ""), used))

        if in_use:
            detail = "\n".join(
                tr("signals.delete_used_line", name=name,
                   blocks=", ".join(b.short_id or b.uuid[:8] for b in used))
                for name, used in in_use
            )
            answer = QMessageBox.warning(
                self, tr("signals.delete_used_title"),
                tr("signals.delete_used_text", detail=detail),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        for row in rows:
            del entries[row]
        self._mark_changed()
        self.refresh()


class SystemSignalsTab(QWidget):
    """The platform catalog, read-only, with a search box.

    Nothing is added here and the panel says why: these names are a
    contract shared by every project and every controller. The column
    that earns its place is the last one - whether THIS platform's
    controller actually computes the signal, or whether the name is
    agreed and nothing produces a value yet. Logic reading a signal
    nobody computes sees its safe default for ever, without an error.
    """

    _COLS = ("id", "description", "type", "direction", "source", "runtime")
    COL_ID, COL_DESCRIPTION, COL_TYPE, COL_DIRECTION, COL_SOURCE, COL_RUNTIME = range(6)

    def __init__(self, studio_window, parent=None):
        super().__init__(parent)
        self._studio_window = studio_window

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        heading = QLabel(tr("signals.system_heading"))
        heading.setObjectName("PanelHeading")
        layout.addWidget(heading)
        intro = QLabel(tr("signals.system_intro"))
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(tr("signals.search"))
        self.search_edit.textChanged.connect(self._apply_filter)
        layout.addWidget(self.search_edit)

        self.table = QTableWidget(0, len(self._COLS))
        self.table.setHorizontalHeaderLabels([tr(f"signals.col_{c}") for c in self._COLS])
        _prep_table(self.table)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        _resizable(self.table, self.COL_ID, 200)
        _resizable(self.table, self.COL_DESCRIPTION, 320)
        _resizable(self.table, self.COL_DIRECTION, 150)
        _resizable(self.table, self.COL_SOURCE, 120)
        _resizable(self.table, self.COL_RUNTIME, 150)
        layout.addWidget(self.table)

        self.count_label = QLabel("")
        layout.addWidget(self.count_label)

        self.refresh()

    def _logic_project(self):
        """Only to pick up this project's own per-device diagnostics
        (<ELA01>.ONLINE and friends), which the catalog generates from
        the device list. Absent editor means the fixed part alone."""
        panel = getattr(self._studio_window, "_logic_panel", None)
        return getattr(panel.main_window(), "project", None) if panel is not None else None

    def refresh(self):
        from shared.logic import system_signals

        signals = system_signals.get_all_signals(self._logic_project())
        self.table.setRowCount(len(signals))
        for row, signal in enumerate(signals):
            self.table.setItem(row, self.COL_ID, _read_only(signal["id"]))
            self.table.setItem(row, self.COL_DESCRIPTION, _read_only(signal.get("description", "")))
            self.table.setItem(row, self.COL_TYPE, _read_only(signal.get("type", "")))
            writable = signal.get("source") == "logic"
            self.table.setItem(row, self.COL_DIRECTION, _read_only(
                tr("signals.direction_write") if writable else tr("signals.direction_read")))
            self.table.setItem(row, self.COL_SOURCE, _read_only(signal.get("source", "")))
            served = signal.get("runtime", "served") == "served"
            self.table.setItem(row, self.COL_RUNTIME, _read_only(
                tr("signals.runtime_served") if served else tr("signals.runtime_planned")))
        self._apply_filter(self.search_edit.text())

    def _apply_filter(self, text: str):
        needle = (text or "").strip().lower()
        shown = 0
        for row in range(self.table.rowCount()):
            haystack = " ".join(
                self.table.item(row, col).text() for col in range(self.table.columnCount())
                if self.table.item(row, col) is not None
            ).lower()
            visible = needle in haystack
            self.table.setRowHidden(row, not visible)
            shown += 1 if visible else 0
        self.count_label.setText(tr("signals.shown_count", shown=shown, total=self.table.rowCount()))


class SignalsPanel(QWidget):
    """The department: the two tabs above, side by side."""

    def __init__(self, studio_window, parent=None):
        super().__init__(parent)
        self._studio_window = studio_window

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        self.internal_tab = InternalSignalsTab(studio_window)
        self.system_tab = SystemSignalsTab(studio_window)
        self.tabs.addTab(self.internal_tab, tr("signals.tab_internal"))
        self.tabs.addTab(self.system_tab, tr("signals.tab_system"))
        layout.addWidget(self.tabs)

    def refresh(self):
        self.internal_tab.refresh()
        self.system_tab.refresh()
