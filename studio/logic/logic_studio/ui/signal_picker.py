"""feat/internal-bits §6 — SignalPickerDialog, modeled on eTango Studio's
"Wybór bitu dla logiki": one dialog handles every signal-typed property
("Bit"/"Sygnał"/"Address" on virtual.*/internal.reg_*/system.signal), with
a `value_type` filter (BOOL/REAL) so a context that can only use one type
never even shows the other.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLineEdit, QPushButton, QDialogButtonBox, QComboBox, QCheckBox,
    QFormLayout, QMessageBox
)
from PySide6.QtCore import Qt
from logic_studio.i18n import tr

SIGNAL_ID_ROLE = Qt.UserRole
KIND_ROLE = Qt.UserRole + 1  # "physical" | "internal" | "system" — for filtering/accept logic


class _NewInternalSignalDialog(QDialog):
    """§6.6: add a registry entry without leaving SignalPickerDialog.

    feat/signal-register §1.5: the TYPE is fixed to the type of the block
    that opened the picker whenever that block only accepts one. Creating
    a BOOL from a register block used to be possible, and the signal then
    simply never appeared in the list it was created from - the registry
    gained an entry nobody asked for and the engineer was left looking
    for it. A disabled combo still SHOWS the type (it is information),
    it just cannot be set to the one value that makes no sense here.
    """

    def __init__(self, value_type: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("signal.new_title"))
        self.entry = None

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.name_edit = QLineEdit()
        self.type_combo = QComboBox()
        # BOOL/REAL are the stored values of the `type` field, not labels -
        # they travel into projekt/.epwlogic and are compared verbatim by
        # the validator and the exporter, so they are deliberately NOT
        # translated. See test_interface_is_translatable's own note.
        self.type_combo.addItems(["BOOL", "REAL"])
        if value_type in ("BOOL", "REAL"):
            self.type_combo.setCurrentText(value_type)
            self.type_combo.setEnabled(False)
            self.type_combo.setToolTip(tr("signal.type_locked", type=value_type))
        self.retentive_check = QCheckBox()
        self.description_edit = QLineEdit()
        self.label_edit = QLineEdit()
        self.category_edit = QLineEdit()
        form.addRow(tr("signal.field_name"), self.name_edit)
        form.addRow(tr("signal.field_type"), self.type_combo)
        form.addRow(tr("signal.field_retentive"), self.retentive_check)
        form.addRow(tr("signal.field_description"), self.description_edit)
        form.addRow(tr("signal.field_label"), self.label_edit)
        form.addRow(tr("signal.field_category"), self.category_edit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self):
        from shared.logic.internal_bits import validate_internal_bit_name
        name = self.name_edit.text().strip()
        error = validate_internal_bit_name(name)
        if error:
            QMessageBox.critical(self, tr("common.invalid_name"), error)
            return
        self.entry = {
            "name": name,
            "type": self.type_combo.currentText(),
            "retentive": self.retentive_check.isChecked(),
            "description": self.description_edit.text(),
            "label": self.label_edit.text(),
            "category": self.category_edit.text(),
        }
        self.accept()


class SignalPickerDialog(QDialog):
    _EMPTY_HINT_ROLE = Qt.UserRole + 2   # marks the "nothing here yet" row

    def __init__(self, project, value_type: str = "BOOL", parent=None, sections=("physical", "internal", "system"), system_source_filter=None):
        """`value_type`: "BOOL"/"REAL" filters every section to that type;
        None shows both (used for system.signal's "Sygnał", which can
        point at either). `sections` restricts which of the three §6.3
        top-level sections are populated at all — system.signal has no use
        for "Physical inputs and outputs"/"Internal signals", so its
        picker passes sections=("system",). `system_source_filter`
        (feat/sswin-signals §2.4) additionally restricts the "system"
        section to catalog entries whose "source" field matches exactly —
        system.signal_out passes "logic" so an engineer configuring an
        OUTPUT block is never offered a source == "runtime" signal it
        could never legally write; None (every other caller) shows every
        system signal regardless of source, unchanged from before."""
        super().__init__(parent)
        self.project = project
        self.value_type = value_type
        self.sections = sections
        self.system_source_filter = system_source_filter
        self._chosen_id = None
        self._chosen_kind = None
        self.setWindowTitle(tr("signal.choose_title"))
        self.resize(640, 480)

        layout = QVBoxLayout(self)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(tr("common.search"))
        self.search_edit.textChanged.connect(self._apply_filter)
        layout.addWidget(self.search_edit)

        # §6.2: two-level tree, three columns — description first (main
        # column, per eTango), technical id in the middle, label on the
        # right.
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([tr("signal.col_description"), tr("signal.col_name"), tr("signal.col_label")])
        self.tree.setColumnWidth(0, 280)
        self.tree.setColumnWidth(1, 180)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.tree)

        new_signal_row = QHBoxLayout()
        self.new_signal_btn = QPushButton(tr("signal.new_button"))
        self.new_signal_btn.clicked.connect(self._create_new_signal)
        # It creates an INTERNAL signal. A picker that does not show the
        # internal section (system.signal's own) would create something
        # its own list could never display.
        self.new_signal_btn.setVisible("internal" in self.sections)
        new_signal_row.addWidget(self.new_signal_btn)
        new_signal_row.addStretch()
        layout.addLayout(new_signal_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.ok_button = buttons.button(QDialogButtonBox.Ok)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._populate()
        self.tree.itemSelectionChanged.connect(self._update_ok_enabled)
        self._update_ok_enabled()

    # ---- population ---------------------------------------------------------

    def _populate(self):
        self.tree.clear()
        from logic_studio.core.device_model import DeviceModel

        # §6.3, section 1: physical IO — sections are visually separated
        # top-level nodes since they carry a completely different character
        # (project-defined vs. platform contract).
        if "physical" in self.sections:
            phys_root = QTreeWidgetItem(self.tree, [tr("signal.section_physical")])
            # feat/io-labels-and-ids §3.2: the Opis column shows the
            # address's own descriptive label (§1) when one is set — "Wyl.
            # Q1 zamknięty" is what an engineer actually recognizes, not
            # the generic "Digital input (ELA)" every one of the 32 DI
            # channels shares. Falls back to that generic description when
            # no label exists yet. Search already scans every column
            # (_filter_subtree), so this alone makes label text searchable
            # too — no separate search-path change needed.
            if self.value_type in (None, "BOOL"):
                for addr in DeviceModel.get_ela_addresses(self.project):
                    desc = DeviceModel.get_io_label(self.project, addr) or "Digital input (ELA)"
                    self._add_leaf(phys_root, desc, addr, "", addr, "physical")
                for addr in DeviceModel.get_ada_addresses(self.project):
                    desc = DeviceModel.get_io_label(self.project, addr) or "Digital output (ADA)"
                    self._add_leaf(phys_root, desc, addr, "", addr, "physical")
            if self.value_type in (None, "REAL"):
                for point in DeviceModel.get_analog_points(self.project):
                    addr = point.get("address", "")
                    desc = DeviceModel.get_io_label(self.project, addr) or point.get("name", "") or addr
                    self._add_leaf(phys_root, desc, addr, point.get("unit", ""), addr, "physical")
            self._hint_if_empty(phys_root, tr("signal.empty_physical"))

        # §6.3, section 2: internal signals, grouped by their own "category".
        if "internal" in self.sections:
            internal_root = QTreeWidgetItem(self.tree, [tr("signal.section_internal")])
            by_category = {}
            for entry in DeviceModel.get_internal_bits(self.project, type_filter=self.value_type):
                cat = entry.get("category") or tr("signal.no_category")
                by_category.setdefault(cat, []).append(entry)
            for cat in sorted(by_category):
                cat_item = QTreeWidgetItem(internal_root, [cat])
                for entry in by_category[cat]:
                    self._add_leaf(
                        cat_item, entry.get("description", ""), entry.get("name", ""),
                        entry.get("label", ""), entry.get("name", ""), "internal",
                    )
            # §1.3: an empty registry is the NORMAL state of a new project,
            # and an empty row under a heading reads as a broken dialog.
            # Say what belongs here and how to put it there.
            self._hint_if_empty(internal_root, tr("signal.empty_internal"))

        # §6.3, section 3: fixed system-signal catalog.
        if "system" in self.sections:
            from shared.logic import system_signals
            sys_root = QTreeWidgetItem(self.tree, [tr("signal.section_system")])
            for cat in system_signals.get_categories(self.project):
                matching = [
                    s for s in cat["signals"]
                    if (self.value_type is None or s["type"] == self.value_type)
                    and (self.system_source_filter is None or s.get("source") == self.system_source_filter)
                ]
                if not matching:
                    continue
                cat_item = QTreeWidgetItem(sys_root, [cat["name"]])
                for sig in matching:
                    self._add_leaf(cat_item, sig["description"], sig["id"], sig.get("label", ""), sig["id"], "system")
            # An OUTPUT block filters the catalog down to source == "logic";
            # for a REAL one that is empty today, and silence would read as
            # "the catalog failed to load".
            self._hint_if_empty(
                sys_root,
                tr("signal.empty_system_writable") if self.system_source_filter == "logic"
                else tr("signal.empty_system"),
            )

        self.tree.expandAll()

    def _hint_if_empty(self, section_item, text):
        """One explanatory row under a section that produced nothing.

        Deliberately NOT a leaf: it carries no SIGNAL_ID_ROLE, so it can
        never be selected, OK stays disabled on it, and _filter_subtree
        keeps treating it as structure rather than as a match. It is
        marked with its own role so the section still counts as empty for
        anything that asks later."""
        if section_item.childCount() > 0:
            return None
        hint = QTreeWidgetItem(section_item, [text])
        hint.setData(0, self._EMPTY_HINT_ROLE, True)
        hint.setFlags(hint.flags() & ~Qt.ItemIsSelectable)
        return hint

    def _add_leaf(self, parent, description, name, label, signal_id, kind):
        item = QTreeWidgetItem(parent, [description, name, label])
        item.setData(0, SIGNAL_ID_ROLE, signal_id)
        item.setData(0, KIND_ROLE, kind)
        return item

    # ---- filtering (§6.5) -----------------------------------------------------

    def _apply_filter(self, text):
        text = text.strip().lower()
        for i in range(self.tree.topLevelItemCount()):
            root = self.tree.topLevelItem(i)
            root_visible = self._filter_subtree(root, text)
            root.setHidden(not root_visible)

    def _filter_subtree(self, item, text) -> bool:
        """Returns True if `item` (or any descendant) should stay visible.
        A leaf (has SIGNAL_ID_ROLE data) matches if `text` appears in any
        of its three columns; a category/section node is visible if any
        child is."""
        if item.data(0, SIGNAL_ID_ROLE) is not None:
            if not text:
                item.setHidden(False)
                return True
            haystack = " ".join(item.text(c) for c in range(3)).lower()
            visible = text in haystack
            item.setHidden(not visible)
            return visible

        if item.data(0, self._EMPTY_HINT_ROLE):
            # The hint belongs to its section, not to the search: it shows
            # while nothing is being searched for and disappears the moment
            # somebody types, when "no results" is the honest answer.
            visible = not text
            item.setHidden(not visible)
            return visible

        any_visible = False
        for i in range(item.childCount()):
            child = item.child(i)
            if self._filter_subtree(child, text):
                any_visible = True
        item.setHidden(not any_visible)
        return any_visible

    # ---- selection ------------------------------------------------------------

    def _selected_leaf(self):
        items = self.tree.selectedItems()
        if not items:
            return None
        item = items[0]
        return item if item.data(0, SIGNAL_ID_ROLE) is not None else None

    def _update_ok_enabled(self):
        self.ok_button.setEnabled(self._selected_leaf() is not None)

    def _on_item_double_clicked(self, item, column):
        if item.data(0, SIGNAL_ID_ROLE) is not None:
            self.tree.setCurrentItem(item)
            self._on_accept()

    def _try_accept_item(self, item):
        if item.data(0, SIGNAL_ID_ROLE) is not None:
            self._on_accept()

    def _on_accept(self):
        leaf = self._selected_leaf()
        if leaf is None:
            return
        self._chosen_id = leaf.data(0, SIGNAL_ID_ROLE)
        self._chosen_kind = leaf.data(0, KIND_ROLE)
        self.accept()

    def selected_signal_id(self):
        """The chosen identifier — an "Address" for physical IO, an
        internal-bit registry NAME (not the M.-prefixed id — that's
        resolved from the name at compile/display time, see §1.2/§2) for
        internal signals, or a system-catalog id. None if the dialog was
        cancelled or nothing was ever selected."""
        return self._chosen_id

    def selected_kind(self):
        """The coarse section the choice came from — "physical" |
        "internal" | "system" (KIND_ROLE). feat/signal-watch: paired with
        selected_signal_id() by callers (core/watch.py's WatchPanel) that
        need core/crossref.py's finer KIND_* classification —
        crossref.classify_signal_id(project, dialog.selected_kind(),
        dialog.selected_signal_id())."""
        return self._chosen_kind

    # ---- §6.6: add a registry entry without leaving the dialog ---------------

    def _create_new_signal(self):
        sub = _NewInternalSignalDialog(self.value_type, parent=self)
        if sub.exec() != QDialog.Accepted or sub.entry is None:
            return

        from shared.logic.internal_bits import validate_internal_bits_registry
        entries = list(self.project.settings.get("internal_bits", []))
        new_lname = sub.entry["name"].lower()
        if any(e.get("name", "").lower() == new_lname for e in entries):
            QMessageBox.critical(self, tr("signal.duplicate"), tr("signal.duplicate_text", name=sub.entry["name"]))
            return

        entries.append(sub.entry)
        errors = validate_internal_bits_registry(entries)
        if errors:
            QMessageBox.critical(self, tr("signal.invalid_entry"), "\n".join(errors))
            return

        self.project.settings["internal_bits"] = entries
        self._populate()

        # Re-select the freshly created entry so the engineer can just hit OK.
        def _find_and_select(item):
            if item.data(0, KIND_ROLE) == "internal" and item.text(1) == sub.entry["name"]:
                self.tree.setCurrentItem(item)
                return True
            for i in range(item.childCount()):
                if _find_and_select(item.child(i)):
                    return True
            return False

        for i in range(self.tree.topLevelItemCount()):
            if _find_and_select(self.tree.topLevelItem(i)):
                break
