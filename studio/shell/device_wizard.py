"""Device wizard - user report: "stwórz kreator urządzenia gdzie krok po
kroku mówi co gdzie dodawać" (a wizard that says, step by step, what to
add and where).

Walks the project's own composition in the order the data depends on
itself - SPEC_PROJEKT_EPW.md's own sections, top to bottom:

    1. project information  (metadata: name, author, description)
    2. device composition   (project.modules)
    3. locations            (project.locations - what cards refer to)
    4. I/O cards            (project.cards - "karty rodzą punkty")
    5. summary + where the rest lives (points, apparatus, screens, logic)

Every page is a plain, self-explaining form; nothing touches the project
until Finish (apply_to_project()), and even then the wizard ADDS and
UPDATES - it never removes a module, a location or a card, since each of
those removals has its own consequences (orphaned data, dangling
addresses) that the regular panels already explain interactively and a
wizard can't. The regular panels stay the place for everything else;
this only gets a new project to the point where they have something to
show.

Reuses the real pieces rather than re-implementing them: project_panels'
_ChannelKindsEditor for a card's channel kinds (the same widget the Cards
table uses), sync_points_for_card() for the points, the same id/location
rules CardsPanel/LocationsPanel enforce (dot/space-free ids,
A-Z0-9 location codes, unique ids/codes/Modbus addresses).
"""
import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QWizard,
    QWizardPage,
)

from studio.shell.i18n import get_language, tr
from studio.shell.project_format import Card, Location
from studio.shell.project_panels import (
    MODULE_CATALOG,
    _ChannelKindsEditor,
    _LOCATION_CODE_RE,
    _next_free_modbus_unit_id,
    _next_unique,
    sync_points_for_card,
)


def _wrapped_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return label


class _IntroPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle(tr("wizard.intro_title"))
        layout = QVBoxLayout(self)
        layout.addWidget(_wrapped_label(tr("wizard.intro_text")))
        layout.addStretch(1)


class _InfoPage(QWizardPage):
    def __init__(self, project):
        super().__init__()
        self.setTitle(tr("wizard.info_title"))
        self.setSubTitle(tr("wizard.info_subtitle"))
        form = QFormLayout(self)
        self.name_edit = QLineEdit(project.metadata.name)
        self.author_edit = QLineEdit(project.metadata.author)
        self.description_edit = QPlainTextEdit(project.metadata.description)
        self.description_edit.setFixedHeight(80)
        form.addRow(tr("wizard.info_name"), self.name_edit)
        form.addRow(tr("wizard.info_author"), self.author_edit)
        form.addRow(tr("wizard.info_description"), self.description_edit)
        # A mandatory field: QWizard keeps Next disabled until it has text.
        self.registerField("project_name*", self.name_edit)

    def validatePage(self) -> bool:
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, tr("wizard.title"), tr("wizard.info_name_required"))
            return False
        return True


class _ModulesPage(QWizardPage):
    def __init__(self, project):
        super().__init__()
        self.setTitle(tr("wizard.modules_title"))
        self.setSubTitle(tr("wizard.modules_subtitle"))
        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        self.checks = {}
        is_pl = get_language() == "pl"
        already = set(project.modules)
        for feature_id, name_pl, name_en, desc_pl, desc_en, _group in MODULE_CATALOG:
            check = QCheckBox(name_pl if is_pl else name_en)
            check.setToolTip(desc_pl if is_pl else desc_en)
            if feature_id in already:
                check.setChecked(True)
                check.setEnabled(False)  # removal is the Device Composition branch's job, not the wizard's
            layout.addWidget(check)
            layout.addWidget(_wrapped_label("    " + (desc_pl if is_pl else desc_en)))
            self.checks[feature_id] = check
        layout.addStretch(1)
        scroll.setWidget(inner)
        outer.addWidget(scroll)

    def chosen_modules(self) -> list:
        return [feature_id for feature_id, check in self.checks.items() if check.isChecked()]


class _LocationsPage(QWizardPage):
    _COL_CODE, _COL_DESCRIPTION = 0, 1

    def __init__(self, project):
        super().__init__()
        self.setTitle(tr("wizard.locations_title"))
        self.setSubTitle(tr("wizard.locations_subtitle"))
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels([tr("cards.col_code"), tr("cards.col_description")])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)
        buttons = QHBoxLayout()
        self.add_button = QPushButton(tr("wizard.locations_add"))
        self.remove_button = QPushButton(tr("wizard.locations_remove"))
        self.add_button.clicked.connect(self.add_row)
        self.remove_button.clicked.connect(self._remove_selected)
        buttons.addWidget(self.add_button)
        buttons.addWidget(self.remove_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        self._existing_codes = {loc.code for loc in project.locations}
        for loc in project.locations:
            self.add_row(loc.code, loc.description)

    def add_row(self, code: str = "", description: str = ""):
        row = self.table.rowCount()
        self.table.insertRow(row)
        code_item = QTableWidgetItem(code)
        if code in self._existing_codes:
            # An existing location's code is what its cards already point
            # at - editable description, fixed code.
            code_item.setFlags(code_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, self._COL_CODE, code_item)
        self.table.setItem(row, self._COL_DESCRIPTION, QTableWidgetItem(description))
        if not code:
            self.table.editItem(code_item)

    def _remove_selected(self):
        row = self.table.currentRow()
        if row < 0:
            return
        if self.table.item(row, self._COL_CODE).text() in self._existing_codes:
            return  # never removes what the project already has - see module docstring
        self.table.removeRow(row)

    def entries(self) -> list:
        """[(code, description), ...] as typed - codes upper-cased and
        stripped, the same normalisation LocationsPanel applies."""
        result = []
        for row in range(self.table.rowCount()):
            code = (self.table.item(row, self._COL_CODE).text() or "").strip().upper()
            description = (self.table.item(row, self._COL_DESCRIPTION).text() or "").strip()
            result.append((code, description))
        return result

    def validatePage(self) -> bool:
        seen = set()
        for code, _description in self.entries():
            if not _LOCATION_CODE_RE.match(code):
                QMessageBox.warning(self, tr("wizard.title"), tr("wizard.locations_invalid", code=code))
                return False
            if code in seen:
                QMessageBox.warning(self, tr("wizard.title"), tr("wizard.locations_duplicate", code=code))
                return False
            seen.add(code)
        return True


class _CardsPage(QWizardPage):
    _COL_ID, _COL_MODEL, _COL_KINDS, _COL_MODBUS, _COL_LOCATION = range(5)

    def __init__(self, project, locations_page: _LocationsPage):
        super().__init__()
        self.setTitle(tr("wizard.cards_title"))
        self.setSubTitle(tr("wizard.cards_subtitle"))
        self._project = project
        self._locations_page = locations_page
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([
            tr("cards.col_id"), tr("cards.col_model"), tr("cards.col_channel_kinds"),
            tr("cards.col_modbus_unit_id"), tr("cards.col_location"),
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setColumnWidth(self._COL_ID, 90)
        self.table.setColumnWidth(self._COL_MODEL, 120)
        self.table.setColumnWidth(self._COL_KINDS, 440)
        self.table.setColumnWidth(self._COL_MODBUS, 90)
        layout.addWidget(self.table)
        buttons = QHBoxLayout()
        self.add_button = QPushButton(tr("wizard.cards_add"))
        self.remove_button = QPushButton(tr("wizard.cards_remove"))
        self.add_button.clicked.connect(lambda: self.add_row())
        self.remove_button.clicked.connect(self._remove_selected)
        buttons.addWidget(self.add_button)
        buttons.addWidget(self.remove_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        self._existing_ids = {card.id for card in project.cards}
        for card in project.cards:
            self.add_row(card)

    def initializePage(self):
        # The location choices come from the page before - refreshed
        # every time this page is entered, since Back/Next can change them.
        codes = [code for code, _d in self._locations_page.entries() if code]
        for row in range(self.table.rowCount()):
            combo = self.table.cellWidget(row, self._COL_LOCATION)
            current = combo.currentData()
            self._fill_location_combo(combo, codes, current)

    @staticmethod
    def _fill_location_combo(combo: QComboBox, codes, current):
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(tr("cards.location_blank"), "")
        for code in codes:
            combo.addItem(code, code)
        idx = combo.findData(current or "")
        combo.setCurrentIndex(idx if idx >= 0 else 0)
        combo.blockSignals(False)

    def _used_modbus_ids(self) -> set:
        used = set()
        for row in range(self.table.rowCount()):
            used.add(self.table.cellWidget(row, self._COL_MODBUS).value())
        return used

    def add_row(self, card: Card = None):
        row = self.table.rowCount()
        # Both "what's taken" scans run BEFORE the new row exists - the
        # new row has no widgets/items yet, so scanning it would crash.
        if card is None:
            taken = {self.table.item(r, self._COL_ID).text() for r in range(row)}
            card = Card(id=_next_unique(taken, "KARTA"), model="", channel_kinds={})
            used = self._used_modbus_ids()
            modbus = next((n for n in range(1, 248) if n not in used), 1)
        else:
            modbus = card.modbus_unit_id or _next_free_modbus_unit_id(self._project, exclude_card=card) or 1
        self.table.insertRow(row)
        id_item = QTableWidgetItem(card.id)
        if card.id in self._existing_ids:
            id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # addresses already depend on it
        self.table.setItem(row, self._COL_ID, id_item)
        self.table.setItem(row, self._COL_MODEL, QTableWidgetItem(card.model))
        kinds = _ChannelKindsEditor()
        kinds.set_channel_kinds(card.channel_kinds)
        self.table.setCellWidget(row, self._COL_KINDS, kinds)
        modbus_spin = QSpinBox()
        modbus_spin.setRange(1, 247)
        modbus_spin.setValue(modbus)
        self.table.setCellWidget(row, self._COL_MODBUS, modbus_spin)
        location_combo = QComboBox()
        codes = [code for code, _d in self._locations_page.entries() if code]
        self._fill_location_combo(location_combo, codes, card.location)
        self.table.setCellWidget(row, self._COL_LOCATION, location_combo)
        self.table.resizeRowToContents(row)

    def _remove_selected(self):
        row = self.table.currentRow()
        if row < 0:
            return
        if self.table.item(row, self._COL_ID).text() in self._existing_ids:
            return  # never removes what the project already has - see module docstring
        self.table.removeRow(row)

    def entries(self) -> list:
        """One Card per row, as typed - not yet in the project."""
        result = []
        for row in range(self.table.rowCount()):
            result.append(Card(
                id=(self.table.item(row, self._COL_ID).text() or "").strip(),
                model=(self.table.item(row, self._COL_MODEL).text() or "").strip(),
                channel_kinds=self.table.cellWidget(row, self._COL_KINDS).channel_kinds(),
                modbus_unit_id=self.table.cellWidget(row, self._COL_MODBUS).value(),
                location=self.table.cellWidget(row, self._COL_LOCATION).currentData() or "",
            ))
        return result

    def validatePage(self) -> bool:
        seen_ids, seen_modbus = set(), set()
        for card in self.entries():
            if not card.id or "." in card.id or " " in card.id:
                QMessageBox.warning(self, tr("wizard.title"), tr("wizard.cards_invalid_id", id=card.id))
                return False
            if card.id in seen_ids:
                QMessageBox.warning(self, tr("wizard.title"), tr("wizard.cards_duplicate_id", id=card.id))
                return False
            seen_ids.add(card.id)
            if not card.channel_kinds:
                QMessageBox.warning(self, tr("wizard.title"), tr("wizard.cards_no_kind", id=card.id))
                return False
            if card.modbus_unit_id in seen_modbus:
                QMessageBox.warning(
                    self, tr("wizard.title"), tr("wizard.cards_duplicate_modbus", unit_id=card.modbus_unit_id)
                )
                return False
            seen_modbus.add(card.modbus_unit_id)
        return True


class _SummaryPage(QWizardPage):
    def __init__(self, wizard):
        super().__init__()
        self._wizard = wizard
        self.setTitle(tr("wizard.summary_title"))
        self.setSubTitle(tr("wizard.summary_subtitle"))
        layout = QVBoxLayout(self)
        self.counts_label = _wrapped_label("")
        layout.addWidget(self.counts_label)
        layout.addWidget(_wrapped_label(tr("wizard.summary_next_heading")))
        self.next_label = _wrapped_label("")
        layout.addWidget(self.next_label)
        layout.addStretch(1)

    def initializePage(self):
        w = self._wizard
        cards = w.cards_page.entries()
        points = sum(sum(card.channel_kinds.values()) for card in cards)
        self.counts_label.setText(tr(
            "wizard.summary_counts",
            name=w.info_page.name_edit.text().strip(),
            modules=len(w.modules_page.chosen_modules()),
            locations=len([code for code, _d in w.locations_page.entries() if code]),
            cards=len(cards),
            points=points,
        ))
        steps = ["next_points", "next_devices", "next_alarm", "next_screens", "next_logic", "next_save"]
        self.next_label.setText("\n".join(f"• {tr('wizard.' + key)}" for key in steps))


class DeviceWizard(QWizard):
    """See the module docstring. `project` is read at construction (to
    prefill) and written only by apply_to_project() - which main_window.
    _run_device_wizard() calls after exec() returns Accepted, so a
    cancelled wizard leaves the project exactly as it found it."""

    def __init__(self, project, parent=None):
        super().__init__(parent)
        self._project = project
        self.setWindowTitle(tr("wizard.title"))
        self.setWizardStyle(QWizard.WizardStyle.ClassicStyle)
        self.setOption(QWizard.WizardOption.NoBackButtonOnStartPage, True)
        self.resize(980, 620)
        self.intro_page = _IntroPage()
        self.info_page = _InfoPage(project)
        self.modules_page = _ModulesPage(project)
        self.locations_page = _LocationsPage(project)
        self.cards_page = _CardsPage(project, self.locations_page)
        self.summary_page = _SummaryPage(self)
        for page in (self.intro_page, self.info_page, self.modules_page, self.locations_page,
                     self.cards_page, self.summary_page):
            self.addPage(page)

    def apply_to_project(self, project=None) -> dict:
        """Writes every page into `project` (default: the one given at
        construction). Add-and-update only - never removes anything, see
        the module docstring. Returns {"cards": n, "points": n,
        "locations": n, "modules": n} of what was ADDED, for the caller's
        own status/report."""
        project = project if project is not None else self._project
        added = {"modules": 0, "locations": 0, "cards": 0, "points": 0}

        project.metadata.name = self.info_page.name_edit.text().strip()
        project.metadata.author = self.info_page.author_edit.text().strip()
        project.metadata.description = self.info_page.description_edit.toPlainText().strip()

        for feature_id in self.modules_page.chosen_modules():
            if feature_id not in project.modules:
                project.modules.append(feature_id)
                added["modules"] += 1

        by_code = {loc.code: loc for loc in project.locations}
        for code, description in self.locations_page.entries():
            if not code:
                continue
            existing = by_code.get(code)
            if existing is None:
                new_location = Location(code=code, description=description)
                project.locations.append(new_location)
                by_code[code] = new_location
                added["locations"] += 1
            else:
                existing.description = description

        by_id = {card.id: card for card in project.cards}
        before = len(project.points)
        for typed in self.cards_page.entries():
            existing = by_id.get(typed.id)
            if existing is None:
                project.cards.append(typed)
                by_id[typed.id] = typed
                added["cards"] += 1
                target = typed
            else:
                existing.model = typed.model
                existing.modbus_unit_id = typed.modbus_unit_id
                existing.location = typed.location
                # A kind unticked here is exactly the removal the wizard
                # promises not to do - keep every kind the card already
                # had; a kind ticked here is added or its count updated.
                merged = dict(existing.channel_kinds)
                merged.update(typed.channel_kinds)
                existing.channel_kinds = merged
                target = existing
            sync_points_for_card(project, target)
        added["points"] = max(0, len(project.points) - before)
        project.touch()
        return added
