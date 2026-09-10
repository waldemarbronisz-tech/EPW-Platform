"""Task "edytor DI/DO/AI" - real panels for three of the tree branches
task 1.4 (main_window.py's own _INACTIVE_CONFIG_CHILDREN) deliberately
left as placeholders: "Informacje o projekcie", "Karty wejść/wyjść",
"Rejestr punktów". SPEC_PROJEKT_EPW.md's own "Kolejność wdrożenia" step
2 is exactly this - "Rejestr punktów w Studio — karty rodzą punkty,
opisy" - built on top of step 1 (project_format.py, already done).

Scope, stated plainly because it matters: this makes the point registry
real WITHIN Studio's own Project object. It does NOT reach into today's
separate Logic Studio (ELA01.DI01-style addressing, device_model.py) -
unifying that address grammar with this one is the still-undecided
"bridge vs migration" question ADDRESSING_INVENTORY.md already raised,
and SPEC_PROJEKT_EPW.md's own rollout order schedules that for a LATER
step (5: "Migracja adresacji"), after this one.

Follow-up ("co jeszcze możemy dorobić") added in the same file:
  - DevicesPanel/PointAssignDialog - SPEC's next section, "Aparaty":
    a device's feedback/command lists are point addresses, and
    find_point_owner() is the actual "Studio ma to wykryć przy
    przypisaniu" check - a point already claimed by one device can't be
    checked into another's list, enforced in the assignment dialog
    itself, not after the fact.
  - Cards/Locations bridge to Synoptic (main_window.py's
    _sync_device_registry_with_synoptic(), synoptic_panel.py's
    query_device_registry()/push_device_registry(), main.tsx's
    __synopticDeviceRegistry/__synopticImportCardsAndLocations) -
    Synoptic's own DeviceSchema.ts already describes nearly this same
    Card/Location shape (CardEntry/LocationEntry) under different field
    names; ADD-ONLY in both directions (see that method's own
    docstring for why a real rename/delete sync is explicitly NOT
    attempted here).
  - Card id / location code validation (uniqueness, and the same
    A-Z0-9 charset Synoptic's own LocationEntry already assumes) - so a
    value this panel accepts is never later rejected once the bridge
    above pushes it across.
"""
import re

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from studio.shell.i18n import tr
from studio.shell.project_format import Card, Device, Location, Point

CHANNEL_KINDS = ["DI", "DO", "AI", "AO"]
_ANALOG_KINDS = {"AI", "AO"}
DEVICE_BEHAVIORS = ["SWITCHED", "SIGNAL", "MEASURED", "MODULATED", "SELECTOR"]

_GREY_READONLY_BG = QColor("#E8E8E8")
_LOCATION_CODE_RE = re.compile(r"^[A-Z0-9]+$")


def _card_channel_addresses(card: Card):
    """`<id>.<kind>.<channel>` for channel in 1..card.channels - the
    SPEC's own card-relative addressing rule (already the same shape
    Synoptic's own ChannelAddress uses, DeviceSchema.ts's own docstring:
    'CARD.KIND.CHANNEL')."""
    return [f"{card.id}.{card.kind}.{n}" for n in range(1, card.channels + 1)]


def points_for_card(project, card: Card):
    addrs = set(_card_channel_addresses(card))
    return [p for p in project.points if p.address in addrs]


def sync_points_for_card(project, card: Card):
    """"Karty rodzą punkty" (SPEC_PROJEKT_EPW.md): makes project.points
    contain exactly one Point per channel of `card`, in address order -
    existing points (and whatever description/location/etc. a user
    already typed into them) are left untouched; missing ones are
    created empty; extra ones (channel count was reduced) are dropped.
    Called after every add/edit of a card, never on a timer - the
    contract's own "nie wpisujesz ich ręcznie" only promises points
    appear/disappear WITH the card, not that Studio watches continuously."""
    wanted = _card_channel_addresses(card)
    existing = {p.address: p for p in project.points if p.address.startswith(f"{card.id}.{card.kind}.")}
    # Drop points whose address belongs to this card but is no longer
    # in range (channel count shrank).
    wanted_set = set(wanted)
    project.points = [
        p for p in project.points
        if not (p.address.startswith(f"{card.id}.{card.kind}.") and p.address not in wanted_set)
    ]
    for addr in wanted:
        if addr not in existing:
            project.points.append(Point(address=addr))
    project.points.sort(key=lambda p: p.address)


def remove_points_for_card(project, card: Card):
    prefix = f"{card.id}.{card.kind}."
    project.points = [p for p in project.points if not p.address.startswith(prefix)]


# -- Synoptic bridge field-name mapping ------------------------------------
# Synoptic's own DeviceSchema.ts: CardEntry{id,model,channelKind,
# channelCount}, LocationEntry{code,description} - same two lists as
# Card/Location here, different field names on the Card side only.
# main_window.py's _sync_device_registry_with_synoptic() is the only
# caller; kept here (not in synoptic_panel.py, which stays a thin JS
# bridge with no knowledge of Studio's own dataclasses).

def card_to_synoptic_dict(card: Card) -> dict:
    return {"id": card.id, "model": card.model, "channelKind": card.kind, "channelCount": card.channels}


def card_from_synoptic_dict(data: dict) -> Card:
    kind = data.get("channelKind") or CHANNEL_KINDS[0]
    try:
        channels = int(data.get("channelCount") or 0)
    except (TypeError, ValueError):
        channels = 0
    return Card(id=data["id"], model=data.get("model", ""), kind=kind, channels=channels)


def location_to_synoptic_dict(location: Location) -> dict:
    return {"code": location.code, "description": location.description}


def location_from_synoptic_dict(data: dict) -> Location:
    return Location(code=data["code"], description=data.get("description", ""))


# -- point ownership (SPEC_PROJEKT_EPW.md "Aparat zużywa punkty") ---------

def find_point_owner(project, address: str, exclude_device_id: str = None):
    """The check SPEC_PROJEKT_EPW.md's own "Aparaty" section asks for:
    "Punkt zajęty przez jeden aparat nie może być przypisany do
    drugiego — Studio ma to wykryć przy przypisaniu, nie przy
    uruchomieniu." Returns the owning Device, or None if `address` is
    free (or only "owned" by `exclude_device_id` itself - the device
    currently being edited re-checking its own existing assignment)."""
    for device in project.devices:
        if device.id == exclude_device_id:
            continue
        if address in device.feedback or address in device.command:
            return device
    return None


def point_owner_map(project) -> dict:
    """address -> device id, for every point actually assigned to some
    device's feedback/command list - "Nie każdy punkt należy do
    aparatu" (SPEC) means most entries are simply absent, not empty."""
    owners = {}
    for device in project.devices:
        for address in device.feedback:
            owners.setdefault(address, device.id)
        for address in device.command:
            owners.setdefault(address, device.id)
    return owners


class ProjectInfoPanel(QWidget):
    """SPEC step 1's own metadata (name/description/author) - the
    project's "home" branch. Lifecycle (Nowy/Otwórz/Zapisz/Zapisz jako)
    lives in this panel's OWN contextual toolbar (menus.py's
    build_project_info_toolbar), deliberately NOT on the fixed top
    toolbar - that one already means "the active aspect's own document"
    (Logic diagram / Synoptic screen) and redefining it would silently
    make those unreachable from Studio's chrome. Two lifecycles, two
    places, both real."""

    changed = Signal()

    def __init__(self, studio_window, parent=None):
        super().__init__(parent)
        self._studio_window = studio_window
        self._loading = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)
        self.name_edit = QLineEdit()
        self.author_edit = QLineEdit()
        self.description_edit = QPlainTextEdit()
        self.description_edit.setFixedHeight(90)
        self.path_label = QLabel()
        self.path_label.setStyleSheet("color: #404040;")
        self.revision_label = QLabel()
        self.revision_label.setStyleSheet("color: #404040;")

        form.addRow(tr("project_info.path"), self.path_label)
        form.addRow(tr("project_info.name"), self.name_edit)
        form.addRow(tr("project_info.author"), self.author_edit)
        form.addRow(tr("project_info.description"), self.description_edit)
        form.addRow(tr("project_info.revision"), self.revision_label)
        layout.addLayout(form)
        layout.addStretch(1)

        self.name_edit.editingFinished.connect(self._apply_name)
        self.author_edit.editingFinished.connect(self._apply_author)
        self.description_edit.textChanged.connect(self._apply_description)

        self.refresh()

    def refresh(self):
        project = self._studio_window._project
        self._loading = True
        self.name_edit.setText(project.metadata.name)
        self.author_edit.setText(project.metadata.author)
        if self.description_edit.toPlainText() != project.metadata.description:
            self.description_edit.setPlainText(project.metadata.description)
        path = self._studio_window._project_path
        self.path_label.setText(str(path) if path else tr("project_info.path_unsaved"))
        self.revision_label.setText(str(project.revision))
        self._loading = False

    def _apply_name(self):
        if self._loading:
            return
        project = self._studio_window._project
        if project.metadata.name != self.name_edit.text():
            project.metadata.name = self.name_edit.text()
            project.touch()
            self._studio_window._on_project_changed()

    def _apply_author(self):
        if self._loading:
            return
        project = self._studio_window._project
        if project.metadata.author != self.author_edit.text():
            project.metadata.author = self.author_edit.text()
            project.touch()
            self._studio_window._on_project_changed()

    def _apply_description(self):
        if self._loading:
            return
        project = self._studio_window._project
        text = self.description_edit.toPlainText()
        if project.metadata.description != text:
            project.metadata.description = text
            project.touch()
            self._studio_window._on_project_changed()


class CardsPanel(QWidget):
    """SPEC's "Sprzęt": Cards (id/model/kind/channels) and Locations
    (code/description) together, same heading the spec itself uses.
    Editing a card's kind/channels re-runs sync_points_for_card() -
    "karty rodzą punkty" happens HERE, not in the point registry panel,
    which only ever shows what cards already produced."""

    _CARD_COLS = ["id", "model", "kind", "channels"]
    _LOCATION_COLS = ["code", "description"]

    def __init__(self, studio_window, parent=None):
        super().__init__(parent)
        self._studio_window = studio_window
        self._loading = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        splitter = QSplitter(Qt.Orientation.Vertical)

        cards_box = QWidget()
        cards_layout = QVBoxLayout(cards_box)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.addWidget(_section_label(tr("cards.cards_heading")))
        self.cards_table = QTableWidget(0, len(self._CARD_COLS))
        self.cards_table.setHorizontalHeaderLabels([
            tr("cards.col_id"), tr("cards.col_model"), tr("cards.col_kind"), tr("cards.col_channels"),
        ])
        _prep_table(self.cards_table)
        self.cards_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        cards_layout.addWidget(self.cards_table)
        splitter.addWidget(cards_box)

        locations_box = QWidget()
        locations_layout = QVBoxLayout(locations_box)
        locations_layout.setContentsMargins(0, 0, 0, 0)
        locations_layout.addWidget(_section_label(tr("cards.locations_heading")))
        self.locations_table = QTableWidget(0, len(self._LOCATION_COLS))
        self.locations_table.setHorizontalHeaderLabels([tr("cards.col_code"), tr("cards.col_description")])
        _prep_table(self.locations_table)
        self.locations_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        locations_layout.addWidget(self.locations_table)
        splitter.addWidget(locations_box)

        layout.addWidget(splitter)

        self.cards_table.itemChanged.connect(self._on_card_item_changed)
        self.locations_table.itemChanged.connect(self._on_location_item_changed)

        self.refresh()

    # -- population -----------------------------------------------------

    def refresh(self):
        self._loading = True
        project = self._studio_window._project
        self.cards_table.setRowCount(0)
        for card in project.cards:
            self._append_card_row(card)
        self.locations_table.setRowCount(0)
        for location in project.locations:
            self._append_location_row(location)
        self._loading = False

    def _append_card_row(self, card: Card):
        row = self.cards_table.rowCount()
        self.cards_table.insertRow(row)
        self.cards_table.setItem(row, 0, QTableWidgetItem(card.id))
        self.cards_table.setItem(row, 1, QTableWidgetItem(card.model))
        kind_combo = QComboBox()
        kind_combo.addItems(CHANNEL_KINDS)
        kind_combo.setCurrentText(card.kind if card.kind in CHANNEL_KINDS else CHANNEL_KINDS[0])
        kind_combo.currentTextChanged.connect(lambda _text, r=row: self._on_card_kind_changed(r))
        self.cards_table.setCellWidget(row, 2, kind_combo)
        self.cards_table.setItem(row, 3, QTableWidgetItem(str(card.channels)))

    def _append_location_row(self, location: Location):
        row = self.locations_table.rowCount()
        self.locations_table.insertRow(row)
        self.locations_table.setItem(row, 0, QTableWidgetItem(location.code))
        self.locations_table.setItem(row, 1, QTableWidgetItem(location.description))

    # -- row add/remove (called by menus.py's build_cards_toolbar) -----

    def add_card(self):
        project = self._studio_window._project
        existing_ids = {c.id for c in project.cards}
        new_id = _next_unique(existing_ids, "KARTA")
        card = Card(id=new_id, model="", kind=CHANNEL_KINDS[0], channels=8)
        project.cards.append(card)
        sync_points_for_card(project, card)
        project.touch()
        self.refresh()
        self._studio_window._on_project_changed()

    def remove_selected_card(self):
        row = self.cards_table.currentRow()
        if row < 0:
            return
        project = self._studio_window._project
        card = project.cards[row]
        reply = QMessageBox.question(
            self, tr("cards.confirm_remove_card_title"),
            tr("cards.confirm_remove_card_text", id=card.id),
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        remove_points_for_card(project, card)
        del project.cards[row]
        project.touch()
        self.refresh()
        self._studio_window._on_project_changed()

    def add_location(self):
        project = self._studio_window._project
        existing_codes = {l.code for l in project.locations}
        new_code = _next_unique(existing_codes, "LOK")
        project.locations.append(Location(code=new_code))
        project.touch()
        self.refresh()
        self._studio_window._on_project_changed()

    def remove_selected_location(self):
        row = self.locations_table.currentRow()
        if row < 0:
            return
        project = self._studio_window._project
        del project.locations[row]
        project.touch()
        self.refresh()
        self._studio_window._on_project_changed()

    # -- edits -----------------------------------------------------------

    def _on_card_item_changed(self, item):
        if self._loading:
            return
        row = item.row()
        project = self._studio_window._project
        card = project.cards[row]
        old_id, old_kind = card.id, card.kind

        new_id = self.cards_table.item(row, 0).text().strip()
        if new_id and new_id != card.id and any(c.id == new_id for c in project.cards if c is not card):
            QMessageBox.warning(self, tr("cards.duplicate_id_title"), tr("cards.duplicate_id_text", id=new_id))
            self._loading = True
            self.cards_table.item(row, 0).setText(card.id)
            self._loading = False
            new_id = card.id
        card.id = new_id or card.id
        card.model = self.cards_table.item(row, 1).text()
        try:
            card.channels = max(0, int(self.cards_table.item(row, 3).text()))
        except ValueError:
            card.channels = card.channels
            self._loading = True
            self.cards_table.item(row, 3).setText(str(card.channels))
            self._loading = False
        if old_id != card.id or old_kind != card.kind:
            # Address prefix changed - the OLD points are orphaned
            # (their address no longer matches anything this card would
            # generate); drop them under the old identity, then
            # regenerate under the new one, same as a fresh card.
            project.points = [
                p for p in project.points if not p.address.startswith(f"{old_id}.{old_kind}.")
            ]
        sync_points_for_card(project, card)
        project.touch()
        self._studio_window._on_project_changed()

    def _on_card_kind_changed(self, row):
        project = self._studio_window._project
        card = project.cards[row]
        combo = self.cards_table.cellWidget(row, 2)
        old_kind = card.kind
        new_kind = combo.currentText()
        if old_kind == new_kind:
            return
        project.points = [p for p in project.points if not p.address.startswith(f"{card.id}.{old_kind}.")]
        card.kind = new_kind
        sync_points_for_card(project, card)
        project.touch()
        self._studio_window._on_project_changed()

    def _on_location_item_changed(self, item):
        if self._loading:
            return
        row = item.row()
        project = self._studio_window._project
        location = project.locations[row]

        new_code = self.locations_table.item(row, 0).text().strip().upper()
        if new_code and new_code != location.code:
            # Synoptic's own LocationEntry convention (DeviceSchema.ts:
            # "A-Z and 0-9 only") - kept identical here so a code this
            # panel accepts is never rejected once the Synoptic bridge
            # (_sync_device_registry_with_synoptic) pushes it across.
            invalid = not _LOCATION_CODE_RE.match(new_code)
            duplicate = any(l.code == new_code for l in project.locations if l is not location)
            if invalid or duplicate:
                key = "cards.invalid_location_code_text" if invalid else "cards.duplicate_location_code_text"
                QMessageBox.warning(self, tr("cards.invalid_location_code_title"), tr(key, code=new_code))
                self._loading = True
                self.locations_table.item(row, 0).setText(location.code)
                self._loading = False
                new_code = location.code
        location.code = new_code or location.code
        location.description = self.locations_table.item(row, 1).text()
        project.touch()
        self._studio_window._on_project_changed()


class PointRegistryPanel(QWidget):
    """SPEC step 2's own point: cards already produced these rows (empty)
    - this panel is where a user actually NAMES a position. Analog-only
    columns (signal_type..decimals) are shown for every row (one fixed
    table, no separate digital/analog view) but disabled + grayed on a
    DI/DO row - "przycisk wyszarzony, nie usunięty", same rule this
    session already applies to toolbar buttons, applied here to cells."""

    _COLS = [
        "address", "description", "location", "technical_note",
        "signal_type", "raw_min", "raw_max", "eng_min", "eng_max", "unit", "decimals",
        "device",
    ]

    def __init__(self, studio_window, parent=None):
        super().__init__(parent)
        self._studio_window = studio_window
        self._loading = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        filter_row = QWidget()
        filter_layout = QHBoxLayout(filter_row)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.addWidget(QLabel(tr("points.filter_card")))
        self.card_filter = QComboBox()
        self.card_filter.currentIndexChanged.connect(self.refresh)
        filter_layout.addWidget(self.card_filter, 1)
        layout.addWidget(filter_row)

        self.table = QTableWidget(0, len(self._COLS))
        self.table.setHorizontalHeaderLabels([tr(f"points.col_{c}") for c in self._COLS])
        _prep_table(self.table)
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 90)
        self.table.setColumnWidth(3, 160)
        layout.addWidget(self.table)

        self.table.itemChanged.connect(self._on_item_changed)

        self.refresh()

    def refresh(self):
        project = self._studio_window._project
        self._loading = True

        current_filter = self.card_filter.currentData()
        self.card_filter.blockSignals(True)
        self.card_filter.clear()
        self.card_filter.addItem(tr("points.filter_all"), None)
        for card in project.cards:
            self.card_filter.addItem(f"{card.id} ({card.kind})", card.id)
        idx = self.card_filter.findData(current_filter)
        self.card_filter.setCurrentIndex(idx if idx >= 0 else 0)
        self.card_filter.blockSignals(False)
        active_filter = self.card_filter.currentData()

        location_codes = [l.code for l in project.locations]
        kind_by_card = {c.id: c.kind for c in project.cards}
        owners = point_owner_map(project)

        # User feedback (real screenshot, KARTA2.DO.* filtered): 7 grey,
        # unusable analog columns dominating the screen when looking at
        # one DI/DO card is noise, not "wyszarzone nie usunięte" (that
        # rule is for a MIXED table, not a single-kind filtered view).
        # Filtered to one card whose kind is digital -> hide them
        # outright; filtered to an analog card, or "Wszystkie karty"
        # (mixed kinds, can't pick one answer), keep them visible.
        filtered_kind = kind_by_card.get(active_filter) if active_filter else None
        hide_analog_cols = filtered_kind is not None and filtered_kind not in _ANALOG_KINDS
        for col in range(4, 11):
            self.table.setColumnHidden(col, hide_analog_cols)

        self.table.setRowCount(0)
        points = sorted(project.points, key=lambda p: p.address)
        for point in points:
            card_id = point.address.split(".", 1)[0] if "." in point.address else point.address
            if active_filter and card_id != active_filter:
                continue
            self._append_point_row(point, kind_by_card.get(card_id, ""), location_codes, owners.get(point.address))
        self._loading = False

    def _append_point_row(self, point: Point, card_kind: str, location_codes, owner_id):
        row = self.table.rowCount()
        self.table.insertRow(row)

        addr_item = QTableWidgetItem(point.address)
        addr_item.setFlags(addr_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        addr_item.setBackground(_GREY_READONLY_BG)
        addr_item.setToolTip(point.address)
        self.table.setItem(row, 0, addr_item)

        self.table.setItem(row, 1, QTableWidgetItem(point.description))

        loc_combo = QComboBox()
        loc_combo.addItem("", "")
        for code in location_codes:
            loc_combo.addItem(code, code)
        idx = loc_combo.findData(point.location)
        loc_combo.setCurrentIndex(idx if idx >= 0 else 0)
        loc_combo.currentIndexChanged.connect(lambda _i, r=row: self._on_location_changed(r))
        self.table.setCellWidget(row, 2, loc_combo)

        self.table.setItem(row, 3, QTableWidgetItem(point.technical_note))

        is_analog = card_kind in _ANALOG_KINDS
        analog_values = {
            "signal_type": point.signal_type or "",
            "raw_min": _fmt(point.raw_min),
            "raw_max": _fmt(point.raw_max),
            "eng_min": _fmt(point.eng_min),
            "eng_max": _fmt(point.eng_max),
            "unit": point.unit or "",
            "decimals": _fmt(point.decimals),
        }
        for col_offset, key in enumerate(["signal_type", "raw_min", "raw_max", "eng_min", "eng_max", "unit", "decimals"]):
            item = QTableWidgetItem(analog_values[key])
            if not is_analog:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                item.setBackground(_GREY_READONLY_BG)
            self.table.setItem(row, 4 + col_offset, item)

        # "Aparat" - read-only, computed from every device's feedback/
        # command lists (point_owner_map()) - SPEC's own "Aparat zużywa
        # punkty": this is the first place that occupancy becomes
        # actually VISIBLE, not just enforced at assignment time.
        device_item = QTableWidgetItem(owner_id or "")
        device_item.setFlags(device_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        device_item.setBackground(_GREY_READONLY_BG)
        if owner_id:
            device_item.setToolTip(owner_id)
        self.table.setItem(row, 11, device_item)

    def _on_location_changed(self, row):
        if self._loading:
            return
        project = self._studio_window._project
        address = self.table.item(row, 0).text()
        point = next((p for p in project.points if p.address == address), None)
        if point is None:
            return
        combo = self.table.cellWidget(row, 2)
        point.location = combo.currentData() or ""
        project.touch()
        self._studio_window._on_project_changed()

    def _on_item_changed(self, item):
        if self._loading:
            return
        row = item.row()
        address_item = self.table.item(row, 0)
        if address_item is None:
            return
        project = self._studio_window._project
        address = address_item.text()
        point = next((p for p in project.points if p.address == address), None)
        if point is None:
            return
        col = item.column()
        text = item.text()
        if col == 1:
            point.description = text
        elif col == 3:
            point.technical_note = text
        elif col == 4:
            point.signal_type = text or None
        elif col in (5, 6, 7, 8):
            field_name = ["raw_min", "raw_max", "eng_min", "eng_max"][col - 5]
            setattr(point, field_name, _parse_float(text))
        elif col == 9:
            point.unit = text or None
        elif col == 10:
            point.decimals = _parse_int(text)
        project.touch()
        self._studio_window._on_project_changed()


class PointAssignDialog(QDialog):
    """SPEC's own "Studio ma to wykryć przy przypisaniu" - a checklist
    of every point in the project; a point already owned by ANOTHER
    device shows who owns it and its checkbox is disabled, not just
    warned about after the fact. Used for both feedback and command
    (same widget, different list) - `field_label` is only what's shown
    in the dialog title, `initial` is the address list to pre-check."""

    def __init__(self, project, device: Device, field_label: str, initial, parent=None):
        super().__init__(parent)
        self.setWindowTitle(field_label)
        self._project = project
        self._device = device

        layout = QVBoxLayout(self)
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        owners = point_owner_map(project)
        initial_set = set(initial)
        for point in sorted(project.points, key=lambda p: p.address):
            label = point.address if not point.description else f"{point.address} — {point.description}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, point.address)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            owner = owners.get(point.address)
            checked = point.address in initial_set
            if owner is not None and owner != device.id:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                item.setText(f"{label}  [{tr('devices.owned_by', id=owner)}]")
                item.setForeground(QColor("#808080"))
            item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
            self.list_widget.addItem(item)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.resize(420, 480)

    def selected_addresses(self):
        result = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                result.append(item.data(Qt.ItemDataRole.UserRole))
        return result


class DevicesPanel(QWidget):
    """SPEC's "Aparaty" section: id/behavior/kind + which points a
    device reads (feedback) and drives (command). Deliberately the
    SPEC's own simpler shape (flat address lists), not Synoptic's own
    richer per-behavior DeviceSchema.ts (diClosed/diOpen/pulseMs/...) -
    that shape belongs to Synoptic's own diagram-bound device form; this
    is Studio's own registry, built the same incremental way Points
    was (a plain, generic version first)."""

    _COLS = ["id", "behavior", "kind", "feedback", "command"]

    def __init__(self, studio_window, parent=None):
        super().__init__(parent)
        self._studio_window = studio_window
        self._loading = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.table = QTableWidget(0, len(self._COLS))
        self.table.setHorizontalHeaderLabels([tr(f"devices.col_{c}") for c in self._COLS])
        _prep_table(self.table)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        self.table.itemChanged.connect(self._on_item_changed)

        self.refresh()

    def refresh(self):
        self._loading = True
        self.table.setRowCount(0)
        for device in self._studio_window._project.devices:
            self._append_row(device)
        self._loading = False

    def _append_row(self, device: Device):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(device.id))

        behavior_combo = QComboBox()
        behavior_combo.addItems(DEVICE_BEHAVIORS)
        behavior_combo.setCurrentText(device.behavior if device.behavior in DEVICE_BEHAVIORS else DEVICE_BEHAVIORS[0])
        behavior_combo.currentTextChanged.connect(lambda _t, r=row: self._on_behavior_changed(r))
        self.table.setCellWidget(row, 1, behavior_combo)

        self.table.setItem(row, 2, QTableWidgetItem(device.kind))

        feedback_btn = QPushButton(self._summary(device.feedback))
        feedback_btn.clicked.connect(lambda _c=False, r=row: self._edit_points(r, "feedback"))
        self.table.setCellWidget(row, 3, feedback_btn)

        command_btn = QPushButton(self._summary(device.command))
        command_btn.clicked.connect(lambda _c=False, r=row: self._edit_points(r, "command"))
        self.table.setCellWidget(row, 4, command_btn)

    @staticmethod
    def _summary(addresses):
        if not addresses:
            return tr("devices.none")
        return tr("devices.n_points", n=len(addresses))

    def add_device(self):
        project = self._studio_window._project
        existing_ids = {d.id for d in project.devices}
        new_id = _next_unique(existing_ids, "APARAT")
        project.devices.append(Device(id=new_id, behavior=DEVICE_BEHAVIORS[0]))
        project.touch()
        self.refresh()
        self._studio_window._on_project_changed()

    def remove_selected_device(self):
        row = self.table.currentRow()
        if row < 0:
            return
        project = self._studio_window._project
        del project.devices[row]
        project.touch()
        self.refresh()
        self._studio_window._on_project_changed()

    def _on_item_changed(self, item):
        if self._loading:
            return
        row = item.row()
        project = self._studio_window._project
        device = project.devices[row]
        if item.column() == 0:
            new_id = self.table.item(row, 0).text().strip()
            if new_id and new_id != device.id and any(d.id == new_id for d in project.devices if d is not device):
                QMessageBox.warning(self, tr("devices.duplicate_id_title"), tr("devices.duplicate_id_text", id=new_id))
                self._loading = True
                self.table.item(row, 0).setText(device.id)
                self._loading = False
                return
            device.id = new_id or device.id
        elif item.column() == 2:
            device.kind = self.table.item(row, 2).text()
        project.touch()
        self._studio_window._on_project_changed()

    def _on_behavior_changed(self, row):
        project = self._studio_window._project
        device = project.devices[row]
        combo = self.table.cellWidget(row, 1)
        device.behavior = combo.currentText()
        project.touch()
        self._studio_window._on_project_changed()

    def _edit_points(self, row, field_name):
        project = self._studio_window._project
        device = project.devices[row]
        label = tr(f"devices.dialog_{field_name}", id=device.id)
        dialog = PointAssignDialog(project, device, label, getattr(device, field_name), self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            setattr(device, field_name, dialog.selected_addresses())
            project.touch()
            self.refresh()
            self._studio_window._on_project_changed()
            if self._studio_window._point_registry_panel is not None:
                self._studio_window._point_registry_panel.refresh()


# -- shared helpers -------------------------------------------------------

def _section_label(text):
    label = QLabel(text)
    f = label.font()
    f.setBold(True)
    label.setFont(f)
    return label


def _prep_table(table: QTableWidget):
    table.verticalHeader().setVisible(False)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setAlternatingRowColors(True)
    # No blanket setStretchLastSection() - each table below stretches
    # its own ONE genuinely free-text column explicitly instead. Two
    # stretch columns (last section on the blanket + a chosen explicit
    # one) would each get half the free space, both cramped.


def _next_unique(existing, prefix):
    n = 1
    while f"{prefix}{n}" in existing:
        n += 1
    return f"{prefix}{n}"


def _fmt(value):
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _parse_float(text):
    text = text.strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _parse_int(text):
    text = text.strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None
