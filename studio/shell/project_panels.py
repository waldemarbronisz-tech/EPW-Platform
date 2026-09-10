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

  - ZonesPanel/LinesPanel/LineConfigDialog ("Alarmówka: na maksa dużo
    opcji") - SPEC's own next section, built to runtime/epw_os/core/
    intrusion_manager.py's REAL, already-executing parameter set (not
    just the contract's terse illustrative subset) - see
    project_format.py's Zone/Line/PowerSupervision docstrings for the
    full field-by-field justification and the one known gap (Line.tag
    is a Point.address, not yet a runtime tag name).

  - ElectricalProtectionPanel/ProcessProtectionPanel ("Zabezpieczenia:
    podział elektryczne/procesowe, na maksa rozbudowujemy") - SPEC's
    "Nastawy zabezpieczeń" section, split exactly the way runtime keeps
    these two domains separate (protection_manager.py vs process_
    protection_manager.py - see project_format.py's own docstring for
    why). Both use the SAME master/detail shape (a list you toggle with
    a switch on the left, a detail form for whatever's selected on the
    right) even though Process's field count would fit inline - one
    recognizable pattern across both, per the task's own "tu również"
    (same treatment, not a smaller one because the domain is simpler).
"""
import os
import re
from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
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
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTextBrowser,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from studio.shell.i18n import tr
from studio.shell.project_format import (
    Card, Device, ELECTRICAL_PROTECTION_ACTIONS, ElectricalProtectionStage, Line,
    LineInputMode, LineParametrization, LineType, Location, NORMAL_STATE_NC, NORMAL_STATE_NO,
    Point, PowerSupervision, ProcessProtection, Zone, default_value_windows,
)

CHANNEL_KINDS = ["DI", "DO", "AI", "AO"]
_ANALOG_KINDS = {"AI", "AO"}
DEVICE_BEHAVIORS = ["SWITCHED", "SIGNAL", "MEASURED", "MODULATED", "SELECTOR"]

# "Skład urządzenia" (task "fix/project-format-integrity", point 2/3) -
# mirrored from runtime/epw_os/core/feature_config.py's own
# TOGGLABLE_FEATURES (GRANICE forbids importing runtime/, so this is a
# hand-copy, same convention as ELECTRICAL_PROTECTION_CATALOG above -
# re-check against that file if it ever changes). ALWAYS_ON_FEATURES
# (main_view/digital_inputs/control_outputs/alarms/events/audit_log)
# are deliberately NOT listed here at all - runtime's own docstring:
# "cannot be disabled by this dialog" - they aren't a CHOICE, so they
# don't belong in a table whose whole point is choosing.
#
# Each entry: (feature_id, name_pl, name_en, description_pl,
# description_en, tree_group). `tree_group` is one of "alarm",
# "protection", or None - which of _refresh_module_visibility()'s
# groups this toggle gates a REAL Studio branch for; None means the
# toggle is real and saved (matches a real runtime feature) but Studio
# has no panel for it yet - shown honestly as such, not hidden.
MODULE_CATALOG = [
    ("intrusion", "Alarmówka", "Intrusion Alarm",
     "Wykrywanie włamań: strefy, linie dozorowe, uzbrajanie/rozbrajanie.",
     "Burglar detection: zones, supervised lines, arming/disarming.", "alarm"),
    ("protection_settings", "Zabezpieczenia elektryczne", "Electrical Protection",
     "Nastawy przekaźnikowe ANSI (napięcie/częstotliwość/prąd/zasilanie), realizowane przez ADA01.",
     "ANSI relay settings (voltage/frequency/current/power supply), executed by ADA01.", "protection"),
    ("protection_process", "Zabezpieczenia procesowe", "Process Protection",
     "Progi górny/dolny na punktach analogowych, oceniane na żywo w runtime.",
     "Upper/lower thresholds on analog points, evaluated live in runtime.", "protection"),
    ("trends", "Trendy", "Trends",
     "Historia wartości punktów procesowych w czasie (Historian).",
     "Historical logging of process point values over time (Historian).", None),
    ("power_quality", "Jakość zasilania", "Power Quality",
     "Monitorowanie parametrów sieci zasilającej (napięcie, THD, asymetria).",
     "Monitoring of mains power parameters (voltage, THD, imbalance).", None),
    ("bus_diagnostics", "Diagnostyka magistrali", "Bus Diagnostics",
     "Liczniki ramek/błędów komunikacji z modułami ELA/ADA/EPM.",
     "Frame/error counters for communication with ELA/ADA/EPM modules.", None),
    ("system_topology", "Topologia systemu", "System Topology",
     "Widok, z jakich modułów i połączeń faktycznie składa się instalacja.",
     "A view of which modules and links the installation actually consists of.", None),
    ("engineer_mode", "Tryb inżynierski", "Engineer Mode",
     "Dodatkowe narzędzia weryfikacyjne dostępne na poziomie dostępu Engineer.",
     "Additional verification tools available at Engineer access level.", None),
    ("analog_inputs", "Wejścia analogowe", "Analog Inputs",
     "Czy ten sterownik w ogóle obsługuje punkty analogowe (AI).",
     "Whether this controller handles analog (AI) points at all.", None),
    ("switching_counters", "Liczniki łączeń", "Switching Counters",
     "Liczba załączeń/wyłączeń i czas pracy aparatów łączeniowych.",
     "Switch/close counts and running time for switching apparatus.", None),
    ("service_notes", "Notatki serwisowe", "Service Notes",
     "Miejsce na wolny tekst serwisanta przy urządzeniach/punktach.",
     "Free-text space for a technician's notes on devices/points.", None),
    ("intrusion_history", "Historia alarmów", "Alarm History",
     "Dziennik zdarzeń alarmówki (uzbrojenia, naruszenia, bypassy) - podstrona Alarmówki w runtime.",
     "The intrusion alarm's own event log (arming, violations, bypasses) - a runtime Alarmówka subpage.", None),
    ("intrusion_config", "Podgląd alarmówki", "Alarm Live View",
     "Żywy podgląd stanu stref i linii na sterowniku - podstrona Alarmówki w runtime.",
     "A live view of zone/line state on the controller - a runtime Alarmówka subpage.", None),
]

MODULE_IDS = [entry[0] for entry in MODULE_CATALOG]


def _module_entry(feature_id):
    for entry in MODULE_CATALOG:
        if entry[0] == feature_id:
            return entry
    return None


def _module_has_data(project, feature_id: str) -> bool:
    """Task 2.4: "gdy projekt ma już dane tego modułu — ostrzeż wprost".
    Only the three modules with a real Studio panel today can HAVE
    Studio-side data at all; the rest (no panel yet) trivially don't."""
    if feature_id == "intrusion":
        return bool(project.zones or project.lines)
    if feature_id == "protection_settings":
        return bool(project.electrical_protection_stages)
    if feature_id == "protection_process":
        return bool(project.process_protections)
    return False


class _ZeroOneSwitch(QWidget):
    """The e²TANGO reference's own two-state switch - "[0][I]", pressed
    segment shows state. The TAK/NIE word is a SEPARATE label the
    caller places next to this (task 3: "stan widoczny słowem, nie samą
    ikoną") - this widget only ever renders the two segments."""

    toggled = Signal(bool)

    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.btn_off = QPushButton("0")
        self.btn_on = QPushButton("I")
        for b in (self.btn_off, self.btn_on):
            b.setCheckable(True)
            b.setFixedWidth(26)
            layout.addWidget(b)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._group.addButton(self.btn_off)
        self._group.addButton(self.btn_on)
        self.set_checked(checked)
        self.btn_on.clicked.connect(lambda: self.toggled.emit(True))
        self.btn_off.clicked.connect(lambda: self.toggled.emit(False))

    def set_checked(self, value: bool):
        (self.btn_on if value else self.btn_off).setChecked(True)


class ModuleCompositionPanel(QWidget):
    """"Skład urządzenia" (task "fix/project-format-integrity", points
    2+3) - SPEC_PROJEKT_EPW.md's own concept, in the e²TANGO layout the
    user pointed at: one table, Nazwa/Opis/Aktywność, [0][I] switches,
    scrollable. Backed by MODULE_CATALOG above (mirrored from runtime's
    real feature_config.py, not guessed) and Project.modules (a plain
    list of enabled feature ids - "moduł spoza składu NIE ISTNIEJE",
    matching presence/absence rather than a stored False).

    Toggling a module OFF that already has real Studio data warns first
    (task 2.4) but never deletes - see _module_has_data()/main_window.
    _refresh_module_visibility(), which is the ONLY thing that reacts to
    a change here (removing/restoring a tree branch), never this panel
    itself touching project.zones/lines/etc."""

    _COLS = ["name", "description", "active"]

    def __init__(self, studio_window, parent=None):
        super().__init__(parent)
        self._studio_window = studio_window
        self._loading = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.table = QTableWidget(0, len(self._COLS))
        self.table.setHorizontalHeaderLabels(
            [tr("modules.col_name"), tr("modules.col_description"), tr("modules.col_active")]
        )
        _prep_table(self.table)
        _make_column_resizable(self.table, 0, 190)
        _make_column_resizable(self.table, 1, 420)
        layout.addWidget(self.table)

        self.refresh()

    def refresh(self):
        from studio.shell.i18n import get_language
        lang = get_language()
        self._loading = True
        self.table.setRowCount(0)
        enabled = set(self._studio_window._project.modules)
        for feature_id, name_pl, name_en, desc_pl, desc_en, _group in MODULE_CATALOG:
            row = self.table.rowCount()
            self.table.insertRow(row)

            name_item = QTableWidgetItem(name_pl if lang == "pl" else name_en)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, name_item)

            desc_item = QTableWidgetItem(desc_pl if lang == "pl" else desc_en)
            desc_item.setFlags(desc_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 1, desc_item)

            cell = QWidget()
            cell_layout = QHBoxLayout(cell)
            cell_layout.setContentsMargins(6, 0, 6, 0)
            cell_layout.setSpacing(8)
            is_on = feature_id in enabled
            label = QLabel(tr("modules.active_yes") if is_on else tr("modules.active_no"))
            label.setMinimumWidth(40)
            switch = _ZeroOneSwitch(checked=is_on)
            switch.toggled.connect(lambda value, fid=feature_id, lbl=label: self._on_toggled(fid, value, lbl))
            cell_layout.addWidget(label)
            cell_layout.addWidget(switch)
            cell_layout.addStretch(1)
            self.table.setCellWidget(row, 2, cell)
        self._loading = False

    def _on_toggled(self, feature_id: str, value: bool, label: QLabel):
        if self._loading:
            return
        project = self._studio_window._project
        currently_enabled = feature_id in project.modules
        if value == currently_enabled:
            return
        if not value and _module_has_data(project, feature_id):
            entry = _module_entry(feature_id)
            from studio.shell.i18n import get_language
            display_name = (entry[1] if get_language() == "pl" else entry[2]) if entry else feature_id
            reply = QMessageBox.question(
                self, tr("modules.confirm_disable_title"),
                tr("modules.confirm_disable_text", name=display_name),
            )
            if reply != QMessageBox.StandardButton.Yes:
                self.refresh()  # snaps the switch back to its real state
                return
        if value:
            project.modules.append(feature_id)
        else:
            project.modules = [m for m in project.modules if m != feature_id]
        label.setText(tr("modules.active_yes") if value else tr("modules.active_no"))
        project.touch()
        self._studio_window._on_project_changed()

    def select_module(self, feature_id: str):
        """Task point 6 - validation report navigation target (the
        "moduł ma dane, ale nie jest w składzie" warning). Row order is
        always MODULE_CATALOG's own fixed order - see refresh() above -
        so no text lookup is needed, unlike the other panels' tables."""
        if feature_id in MODULE_IDS:
            row = MODULE_IDS.index(feature_id)
            if row < self.table.rowCount():
                self.table.setCurrentCell(row, 0)
                self.table.scrollToItem(self.table.item(row, 0))

# "Alarmówka" - state sets per parametrization, same source of truth as
# project_format.default_value_windows() (which state names exist at
# all for EOL vs DEOL) - used to build LineConfigDialog's value-windows
# sub-table with the right ROWS, not just the right default numbers.
_EOL_STATES = ("VIOLATED", "SECURE", "FAULT_OPEN")
_DEOL_STATES = ("SHORT", "VIOLATED", "SECURE", "TAMPER", "FAULT_OPEN")

_GREY_READONLY_BG = QColor("#E8E8E8")
_LOCATION_CODE_RE = re.compile(r"^[A-Z0-9]+$")

# "Zabezpieczenia elektryczne" - hand-copied from runtime/epw_os/core/
# protection_manager.py's own ProtectionManager.init_defaults() (GRANICE
# forbids importing runtime/ from studio/, so this is a COPY, not a
# reference - re-check against that file if it ever changes). The
# catalog itself (which functions/stages exist, their category/source/
# unit, and their FACTORY defaults) is fixed - ADA01 hardware is what
# actually implements these, a project can change a stage's VALUES
# (setting/hysteresis/delay_ms/action/enabled) but not invent a 13th
# function. Each entry: (category, function_id, source, unit,
# [(stage_name, default_setting, default_hysteresis, default_delay_ms,
# default_action), ...]).
ELECTRICAL_PROTECTION_CATALOG = [
    ("Voltage", "27 Under Voltage", "Voltage", "V", [
        ("Stage 1", 200.0, 5.0, 5000, "Warning"),
        ("Stage 2", 180.0, 5.0, 500, "Trip"),
    ]),
    ("Voltage", "59 Over Voltage", "Voltage", "V", [
        ("Stage 1", 245.0, 5.0, 5000, "Warning"),
        ("Stage 2", 255.0, 5.0, 100, "Trip"),
    ]),
    ("Voltage", "59N Neutral Overvoltage", "Voltage N", "V", [
        ("Stage 1", 20.0, 2.0, 1000, "Trip"),
    ]),
    ("Voltage", "47 Phase Sequence / Phase Loss", "Sequence", "", [
        ("Stage 1", 0.0, 0.0, 500, "Trip"),
    ]),
    ("Frequency", "81U Under Frequency", "Frequency", "Hz", [
        ("Stage 1", 49.5, 0.1, 1000, "Warning"),
        ("Stage 2", 48.5, 0.1, 200, "Trip"),
    ]),
    ("Frequency", "81O Over Frequency", "Frequency", "Hz", [
        ("Stage 1", 50.5, 0.1, 1000, "Warning"),
        ("Stage 2", 51.5, 0.1, 200, "Trip"),
    ]),
    ("Current", "50 Instantaneous Overcurrent", "Current", "A", [
        ("Stage 1", 80.0, 5.0, 100, "Trip"),
        ("Stage 2", 120.0, 5.0, 0, "Trip"),
    ]),
    ("Current", "51 Time Overcurrent", "Current", "A", [
        ("Stage 1", 50.0, 2.0, 1000, "Warning"),
        ("Stage 2", 60.0, 2.0, 500, "Trip"),
    ]),
    ("Current", "46 Negative Sequence Current", "Current Neg", "A", [
        ("Stage 1", 10.0, 1.0, 1000, "Trip"),
    ]),
    ("Current", "49 Thermal Overload", "Thermal", "%", [
        ("Stage 1", 90.0, 5.0, 5000, "Warning"),
        ("Stage 2", 100.0, 2.0, 1000, "Trip"),
    ]),
    ("Current", "50N Earth Fault Instantaneous", "Current N", "A", [
        ("Stage 1", 20.0, 1.0, 0, "Trip"),
    ]),
    ("Current", "51N Earth Fault Time", "Current N", "A", [
        ("Stage 1", 10.0, 1.0, 1000, "Trip"),
    ]),
    ("Power/Supply", "Control Voltage Loss", "Control V", "V", [
        ("Stage 1", 20.0, 1.0, 100, "Trip"),
    ]),
    ("Power/Supply", "Technical Supply Loss", "Tech V", "V", [
        ("Stage 1", 200.0, 5.0, 500, "Warning"),
    ]),
    ("Power/Supply", "UPS Supply Loss", "UPS V", "V", [
        ("Stage 1", 200.0, 5.0, 500, "Warning"),
    ]),
]


def ensure_electrical_protection_seeded(project) -> bool:
    """Materializes one ElectricalProtectionStage per catalog entry the
    project doesn't already have (with the catalog's own factory
    defaults) - called on every ElectricalProtectionPanel.refresh(),
    same "the panel guarantees every row exists" role sync_points_for_
    card() has for cards, except the "source" here is the fixed catalog
    above, not a user-added card. Returns True if it changed anything
    (caller's cue to touch()/mark dirty)."""
    existing = {(s.function_id, s.stage_name) for s in project.electrical_protection_stages}
    changed = False
    for _category, function_id, _source, _unit, stages in ELECTRICAL_PROTECTION_CATALOG:
        for stage_name, setting, hysteresis, delay_ms, action in stages:
            if (function_id, stage_name) in existing:
                continue
            project.electrical_protection_stages.append(ElectricalProtectionStage(
                function_id=function_id, stage_name=stage_name,
                setting=setting, hysteresis=hysteresis, delay_ms=delay_ms, action=action,
            ))
            changed = True
    return changed


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
    """"Skład urządzenia" - the physical ELA/ADA/EPM I/O module registry:
    address (id), model, channel kind (DI/DO/AI/AO), channel count -
    SPEC's own "Sprzęt" section, plus each module's own Modbus unit
    address (task: "ELA i ADA i EPM będą łączyły się z orange pi [...]
    po modbus - trzeba dać opcję adresowania") and the one shared bus
    (port/baud, or a TCP gateway) every module sits on - see
    project_format.ModbusBusConfig's own docstring for why this is
    GREENFIELD, not copied from an existing runtime driver. Locations
    moved out to their own LocationsPanel/tree branch (task "ostatnie
    dwa działy"). Editing a card's kind/channels re-runs
    sync_points_for_card() - "karty rodzą punkty" happens HERE, not in
    the point registry panel, which only ever shows what cards already
    produced."""

    _CARD_COLS = ["id", "model", "kind", "channels", "modbus_unit_id"]

    def __init__(self, studio_window, parent=None):
        super().__init__(parent)
        self._studio_window = studio_window
        self._loading = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.cards_table = QTableWidget(0, len(self._CARD_COLS))
        self.cards_table.setHorizontalHeaderLabels([
            tr("cards.col_id"), tr("cards.col_model"), tr("cards.col_kind"), tr("cards.col_channels"),
            tr("cards.col_modbus_unit_id"),
        ])
        _prep_table(self.cards_table)
        _make_column_resizable(self.cards_table, 1, 220)
        layout.addWidget(self.cards_table)

        self.cards_table.itemChanged.connect(self._on_card_item_changed)

        layout.addWidget(_section_label(tr("cards.modbus_bus_heading")))
        bus_form = QFormLayout()
        self.transport_combo = QComboBox()
        self.transport_combo.addItem(tr("cards.modbus_transport_rtu"), "RTU")
        self.transport_combo.addItem(tr("cards.modbus_transport_tcp"), "TCP")
        bus_form.addRow(tr("cards.modbus_transport"), self.transport_combo)
        self.port_edit = QLineEdit()
        bus_form.addRow(tr("cards.modbus_port"), self.port_edit)
        self.baud_spin = QSpinBox()
        self.baud_spin.setRange(300, 921_600)
        bus_form.addRow(tr("cards.modbus_baud"), self.baud_spin)
        self.parity_combo = QComboBox()
        for code, key in (("N", "cards.modbus_parity_n"), ("E", "cards.modbus_parity_e"), ("O", "cards.modbus_parity_o")):
            self.parity_combo.addItem(tr(key), code)
        bus_form.addRow(tr("cards.modbus_parity"), self.parity_combo)
        self.host_edit = QLineEdit()
        bus_form.addRow(tr("cards.modbus_host"), self.host_edit)
        self.tcp_port_spin = QSpinBox()
        self.tcp_port_spin.setRange(1, 65535)
        bus_form.addRow(tr("cards.modbus_tcp_port"), self.tcp_port_spin)
        layout.addLayout(bus_form)

        self.transport_combo.currentIndexChanged.connect(self._on_bus_changed)
        self.port_edit.editingFinished.connect(self._on_bus_changed)
        self.baud_spin.valueChanged.connect(self._on_bus_changed)
        self.parity_combo.currentIndexChanged.connect(self._on_bus_changed)
        self.host_edit.editingFinished.connect(self._on_bus_changed)
        self.tcp_port_spin.valueChanged.connect(self._on_bus_changed)

        self.refresh()

    # -- population -----------------------------------------------------

    def refresh(self):
        self._loading = True
        project = self._studio_window._project
        self.cards_table.setRowCount(0)
        for card in project.cards:
            self._append_card_row(card)

        bus = project.modbus_bus
        idx = self.transport_combo.findData(bus.transport)
        self.transport_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.port_edit.setText(bus.port)
        self.baud_spin.setValue(bus.baud_rate)
        pidx = self.parity_combo.findData(bus.parity)
        self.parity_combo.setCurrentIndex(pidx if pidx >= 0 else 0)
        self.host_edit.setText(bus.host)
        self.tcp_port_spin.setValue(bus.tcp_port)
        self._update_bus_field_visibility()
        self._loading = False

    def _update_bus_field_visibility(self):
        is_rtu = self.transport_combo.currentData() == "RTU"
        for w in (self.port_edit, self.baud_spin, self.parity_combo):
            w.setEnabled(is_rtu)
        for w in (self.host_edit, self.tcp_port_spin):
            w.setEnabled(not is_rtu)

    def _on_bus_changed(self, *_args):
        if self._loading:
            return
        from studio.shell.project_format import ModbusBusConfig
        project = self._studio_window._project
        project.modbus_bus = ModbusBusConfig(
            transport=self.transport_combo.currentData(),
            port=self.port_edit.text(),
            baud_rate=self.baud_spin.value(),
            parity=self.parity_combo.currentData(),
            data_bits=project.modbus_bus.data_bits,
            stop_bits=project.modbus_bus.stop_bits,
            host=self.host_edit.text(),
            tcp_port=self.tcp_port_spin.value(),
        )
        self._update_bus_field_visibility()
        project.touch()
        self._studio_window._on_project_changed()

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
        self.cards_table.setItem(row, 4, QTableWidgetItem(_fmt(card.modbus_unit_id)))

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
        modbus_text = self.cards_table.item(row, 4).text().strip()
        if not modbus_text:
            card.modbus_unit_id = None
        else:
            try:
                unit_id = int(modbus_text)
                if not (1 <= unit_id <= 247):
                    raise ValueError
                card.modbus_unit_id = unit_id
            except ValueError:
                QMessageBox.warning(
                    self, tr("cards.invalid_modbus_unit_title"), tr("cards.invalid_modbus_unit_text")
                )
                self._loading = True
                self.cards_table.item(row, 4).setText(_fmt(card.modbus_unit_id))
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


class LocationsPanel(QWidget):
    """"Lokalizacje" - its own tree branch again (task "ostatnie dwa
    działy"), same data (project.locations) CardsPanel used to also
    show inline. code/description, SPEC's own "Sprzęt" fields."""

    _COLS = ["code", "description"]

    def __init__(self, studio_window, parent=None):
        super().__init__(parent)
        self._studio_window = studio_window
        self._loading = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.table = QTableWidget(0, len(self._COLS))
        self.table.setHorizontalHeaderLabels([tr("cards.col_code"), tr("cards.col_description")])
        _prep_table(self.table)
        _make_column_resizable(self.table, 1, 320)
        layout.addWidget(self.table)

        self.table.itemChanged.connect(self._on_item_changed)

        self.refresh()

    def refresh(self):
        self._loading = True
        self.table.setRowCount(0)
        for location in self._studio_window._project.locations:
            self._append_row(location)
        self._loading = False

    def _append_row(self, location: Location):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(location.code))
        self.table.setItem(row, 1, QTableWidgetItem(location.description))

    def add_location(self):
        project = self._studio_window._project
        existing_codes = {l.code for l in project.locations}
        new_code = _next_unique(existing_codes, "LOK")
        project.locations.append(Location(code=new_code))
        project.touch()
        self.refresh()
        self._studio_window._on_project_changed()

    def remove_selected_location(self):
        row = self.table.currentRow()
        if row < 0:
            return
        project = self._studio_window._project
        del project.locations[row]
        project.touch()
        self.refresh()
        self._studio_window._on_project_changed()

    def _on_item_changed(self, item):
        if self._loading:
            return
        row = item.row()
        project = self._studio_window._project
        location = project.locations[row]

        new_code = self.table.item(row, 0).text().strip().upper()
        if new_code and new_code != location.code:
            invalid = not _LOCATION_CODE_RE.match(new_code)
            duplicate = any(l.code == new_code for l in project.locations if l is not location)
            if invalid or duplicate:
                key = "cards.invalid_location_code_text" if invalid else "cards.duplicate_location_code_text"
                QMessageBox.warning(self, tr("cards.invalid_location_code_title"), tr(key, code=new_code))
                self._loading = True
                self.table.item(row, 0).setText(location.code)
                self._loading = False
                new_code = location.code
        location.code = new_code or location.code
        location.description = self.table.item(row, 1).text()
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
        _make_column_resizable(self.table, 1, 260)
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

    def select_address(self, address: str):
        """Task point 6 - "klik przenosi do miejsca problemu": the
        validation report's own navigation target for every point-
        registry-related issue. Clears the card filter first (the
        offending point might belong to a card the filter is currently
        hiding), then finds the row by address - same string this
        panel's own column 0 always holds, see _append_point_row above."""
        idx = self.card_filter.findData(None)
        if idx >= 0:
            self.card_filter.setCurrentIndex(idx)
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item is not None and item.text() == address:
                self.table.setCurrentCell(row, 1)
                self.table.scrollToItem(item)
                return

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
        _make_column_resizable(self.table, 2, 260)
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

    def select_device(self, device_id: str):
        """Task point 6 - validation report navigation target."""
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item is not None and item.text() == device_id:
                self.table.setCurrentCell(row, 0)
                self.table.scrollToItem(item)
                return

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


def points_of_kind(project, kind: str):
    """Every point whose card has channel kind `kind` - the same
    DI-only / AI-only restriction intrusion_manager.py's own
    list_digital_input_candidates()/list_analog_input_candidates()
    enforce on the runtime side (CONTACT lines only ever get a BOOL/DI
    tag, PARAMETRIZED lines only ever get a REAL/AI tag) - mirrored
    here so LineConfigDialog's own point picker can't offer the wrong
    kind in the first place, same "impossible to assign the wrong type"
    stance as that module's own picker."""
    kind_by_card = {c.id: c.kind for c in project.cards}
    result = []
    for point in sorted(project.points, key=lambda p: p.address):
        card_id = point.address.split(".", 1)[0] if "." in point.address else point.address
        if kind_by_card.get(card_id) == kind:
            result.append(point)
    return result


class ZonesPanel(QWidget):
    """SPEC's "Alarmówka": a zone (strefa) - name + exit/entry delay,
    both real fields on intrusion_manager.IntrusionManager.add_zone().
    Removal refused (with a message) while lines still reference the
    zone - same "don't silently orphan a reference" stance
    IntrusionManager.remove_zone() itself already has on the runtime
    side, enforced here too since Studio has no other check for it."""

    _COLS = ["id", "name", "exit_delay", "entry_delay"]

    def __init__(self, studio_window, parent=None):
        super().__init__(parent)
        self._studio_window = studio_window
        self._loading = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.table = QTableWidget(0, len(self._COLS))
        self.table.setHorizontalHeaderLabels([tr(f"zones.col_{c}") for c in self._COLS])
        _prep_table(self.table)
        _make_column_resizable(self.table, 1, 260)
        layout.addWidget(self.table)

        self.table.itemChanged.connect(self._on_item_changed)

        layout.addWidget(_section_label(tr("zones.power_heading")))
        power_form = QFormLayout()
        self.mains_tag_combo = QComboBox()
        self.mains_ok_check = QCheckBox(tr("zones.ok_state_high"))
        self.battery_tag_combo = QComboBox()
        self.battery_ok_check = QCheckBox(tr("zones.ok_state_high"))
        mains_row = QHBoxLayout()
        mains_row.addWidget(self.mains_tag_combo, 1)
        mains_row.addWidget(self.mains_ok_check)
        battery_row = QHBoxLayout()
        battery_row.addWidget(self.battery_tag_combo, 1)
        battery_row.addWidget(self.battery_ok_check)
        power_form.addRow(tr("zones.mains_tag"), mains_row)
        power_form.addRow(tr("zones.battery_tag"), battery_row)
        layout.addLayout(power_form)
        layout.addStretch(1)

        self.mains_tag_combo.currentIndexChanged.connect(self._on_power_changed)
        self.mains_ok_check.toggled.connect(self._on_power_changed)
        self.battery_tag_combo.currentIndexChanged.connect(self._on_power_changed)
        self.battery_ok_check.toggled.connect(self._on_power_changed)

        self.refresh()

    def refresh(self):
        self._loading = True
        project = self._studio_window._project
        self.table.setRowCount(0)
        for zone in project.zones:
            self._append_row(zone)

        ai_points = points_of_kind(project, "AI")
        ps = project.power_supervision
        for combo, tag in ((self.mains_tag_combo, ps.mains_tag), (self.battery_tag_combo, ps.battery_tag)):
            combo.blockSignals(True)
            combo.clear()
            combo.addItem(tr("zones.not_supervised"), None)
            for point in ai_points:
                label = point.address if not point.description else f"{point.address} — {point.description}"
                combo.addItem(label, point.address)
            idx = combo.findData(tag)
            combo.setCurrentIndex(idx if idx >= 0 else 0)
            combo.blockSignals(False)
        self.mains_ok_check.blockSignals(True)
        self.mains_ok_check.setChecked(ps.mains_ok_state)
        self.mains_ok_check.blockSignals(False)
        self.battery_ok_check.blockSignals(True)
        self.battery_ok_check.setChecked(ps.battery_ok_state)
        self.battery_ok_check.blockSignals(False)
        self._loading = False

    def _append_row(self, zone: Zone):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(zone.id))
        self.table.setItem(row, 1, QTableWidgetItem(zone.name))
        self.table.setItem(row, 2, QTableWidgetItem(_fmt(zone.exit_delay_seconds)))
        self.table.setItem(row, 3, QTableWidgetItem(_fmt(zone.entry_delay_seconds)))

    def add_zone(self):
        project = self._studio_window._project
        existing_ids = {z.id for z in project.zones}
        new_id = _next_unique(existing_ids, "Z")
        project.zones.append(Zone(id=new_id, name=tr("zones.default_name", id=new_id)))
        project.touch()
        self.refresh()
        self._studio_window._on_project_changed()

    def remove_selected_zone(self):
        row = self.table.currentRow()
        if row < 0:
            return
        project = self._studio_window._project
        zone = project.zones[row]
        if any(l.zone_id == zone.id for l in project.lines):
            QMessageBox.warning(self, tr("zones.in_use_title"), tr("zones.in_use_text", id=zone.id))
            return
        del project.zones[row]
        project.touch()
        self.refresh()
        self._studio_window._on_project_changed()

    def _on_item_changed(self, item):
        if self._loading:
            return
        row = item.row()
        project = self._studio_window._project
        zone = project.zones[row]
        new_id = self.table.item(row, 0).text().strip()
        if new_id and new_id != zone.id:
            if any(z.id == new_id for z in project.zones if z is not zone):
                QMessageBox.warning(self, tr("zones.duplicate_id_title"), tr("zones.duplicate_id_text", id=new_id))
                self._loading = True
                self.table.item(row, 0).setText(zone.id)
                self._loading = False
                new_id = zone.id
            else:
                for line in project.lines:
                    if line.zone_id == zone.id:
                        line.zone_id = new_id
        zone.id = new_id or zone.id
        zone.name = self.table.item(row, 1).text()
        zone.exit_delay_seconds = _parse_float(self.table.item(row, 2).text()) or 0.0
        zone.entry_delay_seconds = _parse_float(self.table.item(row, 3).text()) or 0.0
        project.touch()
        self._studio_window._on_project_changed()
        if self._studio_window._lines_panel is not None:
            self._studio_window._lines_panel.refresh()

    def _on_power_changed(self):
        if self._loading:
            return
        project = self._studio_window._project
        project.power_supervision = PowerSupervision(
            mains_tag=self.mains_tag_combo.currentData(),
            mains_ok_state=self.mains_ok_check.isChecked(),
            battery_tag=self.battery_tag_combo.currentData(),
            battery_ok_state=self.battery_ok_check.isChecked(),
        )
        project.touch()
        self._studio_window._on_project_changed()


class LineConfigDialog(QDialog):
    """The full, real intrusion_manager.add_line()/update_line()
    parameter set (see project_format.Line's own docstring) - kept out
    of LinesPanel's table (14 fields is not a table row) the same way
    PointAssignDialog keeps Devices' point lists out of DevicesPanel's
    table."""

    def __init__(self, project, line: Line, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("lines.dialog_title", id=line.id))
        self._project = project
        self._line = line
        self.resize(480, 640)

        outer = QVBoxLayout(self)

        input_box = QGroupBox(tr("lines.group_input"))
        input_form = QFormLayout(input_box)
        self.mode_combo = QComboBox()
        self.mode_combo.addItem(tr("lines.mode_contact"), LineInputMode.CONTACT)
        self.mode_combo.addItem(tr("lines.mode_parametrized"), LineInputMode.PARAMETRIZED)
        input_form.addRow(tr("lines.input_mode"), self.mode_combo)

        self.point_combo = QComboBox()
        input_form.addRow(tr("lines.point"), self.point_combo)

        self.normal_state_combo = QComboBox()
        self.normal_state_combo.addItem(tr("lines.normal_state_nc"), NORMAL_STATE_NC)
        self.normal_state_combo.addItem(tr("lines.normal_state_no"), NORMAL_STATE_NO)
        input_form.addRow(tr("lines.normal_state"), self.normal_state_combo)

        self.parametrization_combo = QComboBox()
        self.parametrization_combo.addItem(tr("lines.parametrization_eol"), LineParametrization.EOL)
        self.parametrization_combo.addItem(tr("lines.parametrization_deol"), LineParametrization.DEOL)
        input_form.addRow(tr("lines.parametrization"), self.parametrization_combo)
        outer.addWidget(input_box)

        self.windows_box = QGroupBox(tr("lines.group_windows"))
        windows_layout = QVBoxLayout(self.windows_box)
        self.windows_table = QTableWidget(0, 2)
        self.windows_table.setHorizontalHeaderLabels([tr("lines.col_min"), tr("lines.col_max")])
        _prep_table(self.windows_table)
        windows_layout.addWidget(self.windows_table)
        outer.addWidget(self.windows_box)

        filter_box = QGroupBox(tr("lines.group_filtering"))
        filter_form = QFormLayout(filter_box)
        self.debounce_spin = _seconds_spinbox()
        filter_form.addRow(tr("lines.min_violation_seconds"), self.debounce_spin)
        self.multiplicity_spin = QSpinBox()
        self.multiplicity_spin.setRange(1, 99)
        filter_form.addRow(tr("lines.multiplicity_count"), self.multiplicity_spin)
        self.multiplicity_window_spin = _seconds_spinbox()
        filter_form.addRow(tr("lines.multiplicity_window_seconds"), self.multiplicity_window_spin)
        self.lockout_spin = QSpinBox()
        self.lockout_spin.setRange(0, 99)
        self.lockout_spin.setSpecialValueText(tr("lines.off"))
        filter_form.addRow(tr("lines.lockout_after_count"), self.lockout_spin)
        self.alarm_hold_spin = _seconds_spinbox()
        filter_form.addRow(tr("lines.alarm_hold_seconds"), self.alarm_hold_spin)
        outer.addWidget(filter_box)

        supervision_box = QGroupBox(tr("lines.group_supervision"))
        supervision_form = QFormLayout(supervision_box)
        self.silence_spin = _seconds_spinbox()
        self.silence_spin.setSpecialValueText(tr("lines.off"))
        supervision_form.addRow(tr("lines.silence_threshold_seconds"), self.silence_spin)
        outer.addWidget(supervision_box)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        self.parametrization_combo.currentIndexChanged.connect(self._on_parametrization_changed)

        self._load_from_line()

    def _load_from_line(self):
        line = self._line
        idx = self.mode_combo.findData(line.input_mode)
        self.mode_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._refresh_point_choices()
        point_idx = self.point_combo.findData(line.tag)
        self.point_combo.setCurrentIndex(point_idx if point_idx >= 0 else -1)
        self.normal_state_combo.setCurrentIndex(self.normal_state_combo.findData(line.normal_state))
        param_idx = self.parametrization_combo.findData(line.parametrization or LineParametrization.EOL)
        self.parametrization_combo.setCurrentIndex(param_idx if param_idx >= 0 else 0)
        self._populate_windows_table(line.value_windows or default_value_windows(
            line.parametrization or LineParametrization.EOL
        ))
        self.debounce_spin.setValue(line.min_violation_seconds)
        self.multiplicity_spin.setValue(max(1, line.multiplicity_count))
        self.multiplicity_window_spin.setValue(line.multiplicity_window_seconds)
        self.lockout_spin.setValue(line.lockout_after_count)
        self.alarm_hold_spin.setValue(line.alarm_hold_seconds)
        self.silence_spin.setValue(line.silence_threshold_seconds)
        self._on_mode_changed()

    def _refresh_point_choices(self):
        mode = self.mode_combo.currentData()
        kind = "AI" if mode == LineInputMode.PARAMETRIZED else "DI"
        current = self.point_combo.currentData()
        self.point_combo.blockSignals(True)
        self.point_combo.clear()
        for point in points_of_kind(self._project, kind):
            label = point.address if not point.description else f"{point.address} — {point.description}"
            self.point_combo.addItem(label, point.address)
        idx = self.point_combo.findData(current)
        self.point_combo.setCurrentIndex(idx if idx >= 0 else -1)
        self.point_combo.blockSignals(False)

    def _populate_windows_table(self, windows: dict):
        states = _DEOL_STATES if self.parametrization_combo.currentData() == LineParametrization.DEOL else _EOL_STATES
        self.windows_table.setRowCount(0)
        for state in states:
            row = self.windows_table.rowCount()
            self.windows_table.insertRow(row)
            self.windows_table.setVerticalHeaderItem(row, QTableWidgetItem(tr(f"lines.state_{state.lower()}")))
            lo, hi = (windows.get(state) or [0.0, 0.0])[:2]
            self.windows_table.setItem(row, 0, QTableWidgetItem(_fmt(lo)))
            self.windows_table.setItem(row, 1, QTableWidgetItem(_fmt(hi)))
        self.windows_table.verticalHeader().setVisible(True)

    def _on_mode_changed(self):
        is_parametrized = self.mode_combo.currentData() == LineInputMode.PARAMETRIZED
        self._refresh_point_choices()
        self.parametrization_combo.setEnabled(is_parametrized)
        self.windows_box.setEnabled(is_parametrized)

    def _on_parametrization_changed(self):
        self._populate_windows_table(default_value_windows(self.parametrization_combo.currentData()))

    def apply_to_line(self):
        line = self._line
        line.input_mode = self.mode_combo.currentData()
        line.tag = self.point_combo.currentData() or ""
        line.normal_state = self.normal_state_combo.currentData()
        if line.input_mode == LineInputMode.PARAMETRIZED:
            line.parametrization = self.parametrization_combo.currentData()
            windows = {}
            states = _DEOL_STATES if line.parametrization == LineParametrization.DEOL else _EOL_STATES
            for row, state in enumerate(states):
                lo = _parse_float(self.windows_table.item(row, 0).text()) or 0.0
                hi = _parse_float(self.windows_table.item(row, 1).text()) or 0.0
                windows[state] = [lo, hi]
            line.value_windows = windows
        else:
            line.parametrization = None
            line.value_windows = {}
        line.min_violation_seconds = self.debounce_spin.value()
        line.multiplicity_count = self.multiplicity_spin.value()
        line.multiplicity_window_seconds = self.multiplicity_window_spin.value()
        line.lockout_after_count = self.lockout_spin.value()
        line.alarm_hold_seconds = self.alarm_hold_spin.value()
        line.silence_threshold_seconds = self.silence_spin.value()


def _seconds_spinbox():
    spin = QDoubleSpinBox()
    spin.setRange(0.0, 3600.0)
    spin.setDecimals(1)
    spin.setSuffix(" s")
    return spin


class LinesPanel(QWidget):
    """SPEC's "Alarmówka": one row per line (id/name/zone/type), a
    "Konfiguruj..." button opening LineConfigDialog for everything else
    (see that dialog's own docstring for why it isn't inline table
    columns)."""

    _COLS = ["id", "name", "zone", "line_type", "config"]

    def __init__(self, studio_window, parent=None):
        super().__init__(parent)
        self._studio_window = studio_window
        self._loading = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.table = QTableWidget(0, len(self._COLS))
        self.table.setHorizontalHeaderLabels([tr(f"lines.col_{c}") for c in self._COLS])
        _prep_table(self.table)
        _make_column_resizable(self.table, 1, 220)
        layout.addWidget(self.table)

        self.table.itemChanged.connect(self._on_item_changed)

        self.refresh()

    def refresh(self):
        self._loading = True
        self.table.setRowCount(0)
        for line in self._studio_window._project.lines:
            self._append_row(line)
        self._loading = False

    def _append_row(self, line: Line):
        project = self._studio_window._project
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(line.id))
        self.table.setItem(row, 1, QTableWidgetItem(line.name))

        zone_combo = QComboBox()
        for zone in project.zones:
            zone_combo.addItem(f"{zone.name} ({zone.id})", zone.id)
        idx = zone_combo.findData(line.zone_id)
        zone_combo.setCurrentIndex(idx if idx >= 0 else -1)
        zone_combo.currentIndexChanged.connect(lambda _i, r=row: self._on_zone_changed(r))
        self.table.setCellWidget(row, 2, zone_combo)

        type_combo = QComboBox()
        for line_type in LineType.ALL:
            type_combo.addItem(tr(f"lines.type_{line_type.lower()}"), line_type)
        idx = type_combo.findData(line.line_type)
        type_combo.setCurrentIndex(idx if idx >= 0 else 0)
        type_combo.currentIndexChanged.connect(lambda _i, r=row: self._on_type_changed(r))
        self.table.setCellWidget(row, 3, type_combo)

        config_btn = QPushButton(self._summary(line))
        config_btn.clicked.connect(lambda _c=False, r=row: self._configure(r))
        self.table.setCellWidget(row, 4, config_btn)

    @staticmethod
    def _summary(line: Line):
        mode_key = "lines.mode_parametrized" if line.input_mode == LineInputMode.PARAMETRIZED else "lines.mode_contact"
        point = line.tag or tr("lines.no_point")
        if line.input_mode == LineInputMode.PARAMETRIZED and line.parametrization:
            return f"{line.parametrization} — {point}"
        return f"{tr(mode_key)} — {point}"

    def select_line(self, line_id: str):
        """Task point 6 - validation report navigation target."""
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item is not None and item.text() == line_id:
                self.table.setCurrentCell(row, 0)
                self.table.scrollToItem(item)
                return

    def add_line(self):
        project = self._studio_window._project
        if not project.zones:
            QMessageBox.warning(self, tr("lines.no_zones_title"), tr("lines.no_zones_text"))
            return
        existing_ids = {l.id for l in project.lines}
        new_id = _next_unique(existing_ids, "L")
        project.lines.append(Line(id=new_id, name=tr("lines.default_name", id=new_id), zone_id=project.zones[0].id))
        project.touch()
        self.refresh()
        self._studio_window._on_project_changed()

    def remove_selected_line(self):
        row = self.table.currentRow()
        if row < 0:
            return
        project = self._studio_window._project
        del project.lines[row]
        project.touch()
        self.refresh()
        self._studio_window._on_project_changed()

    def _on_item_changed(self, item):
        if self._loading:
            return
        row = item.row()
        project = self._studio_window._project
        line = project.lines[row]
        if item.column() == 0:
            new_id = self.table.item(row, 0).text().strip()
            if new_id and new_id != line.id and any(l.id == new_id for l in project.lines if l is not line):
                QMessageBox.warning(self, tr("lines.duplicate_id_title"), tr("lines.duplicate_id_text", id=new_id))
                self._loading = True
                self.table.item(row, 0).setText(line.id)
                self._loading = False
                return
            line.id = new_id or line.id
        elif item.column() == 1:
            line.name = self.table.item(row, 1).text()
        project.touch()
        self._studio_window._on_project_changed()

    def _on_zone_changed(self, row):
        project = self._studio_window._project
        line = project.lines[row]
        combo = self.table.cellWidget(row, 2)
        line.zone_id = combo.currentData()
        project.touch()
        self._studio_window._on_project_changed()

    def _on_type_changed(self, row):
        project = self._studio_window._project
        line = project.lines[row]
        combo = self.table.cellWidget(row, 3)
        line.line_type = combo.currentData()
        project.touch()
        self._studio_window._on_project_changed()

    def _configure(self, row):
        project = self._studio_window._project
        line = project.lines[row]
        dialog = LineConfigDialog(project, line, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            dialog.apply_to_line()
            project.touch()
            self.refresh()
            self._studio_window._on_project_changed()


class ElectricalProtectionPanel(QWidget):
    """SPEC's "Nastawy zabezpieczeń" (electrical side). Left: a tree,
    Category > Function > Stage, each Stage row carries the toggle
    switch ("zaznaczamy które mają być aktywne przełącznikami" - a
    checkbox IS that switch, same convention Qt trees already use for
    this). Right: the selected stage's own detail form. The tree's
    STRUCTURE is the fixed catalog above - never editable here, only
    each stage's enabled/setting/hysteresis/delay_ms/action."""

    def __init__(self, studio_window, parent=None):
        super().__init__(parent)
        self._studio_window = studio_window
        self._loading = False
        self._current_key = None  # (function_id, stage_name) or None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([tr("electrical.col_tree")])
        self.tree.itemChanged.connect(self._on_tree_item_changed)
        self.tree.currentItemChanged.connect(self._on_selection_changed)
        splitter.addWidget(self.tree)

        self.detail_box = QGroupBox(tr("electrical.detail_heading"))
        form = QFormLayout(self.detail_box)
        self.enabled_check = QCheckBox(tr("electrical.enabled"))
        form.addRow(self.enabled_check)
        self.source_label = QLabel()
        form.addRow(tr("electrical.source"), self.source_label)
        self.setting_spin = QDoubleSpinBox()
        self.setting_spin.setRange(-1_000_000.0, 1_000_000.0)
        self.setting_spin.setDecimals(2)
        form.addRow(tr("electrical.setting"), self.setting_spin)
        self.hysteresis_spin = QDoubleSpinBox()
        self.hysteresis_spin.setRange(0.0, 1_000_000.0)
        self.hysteresis_spin.setDecimals(2)
        form.addRow(tr("electrical.hysteresis"), self.hysteresis_spin)
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(0, 3_600_000)
        self.delay_spin.setSuffix(" ms")
        form.addRow(tr("electrical.delay_ms"), self.delay_spin)
        self.action_combo = QComboBox()
        self.action_combo.addItems(ELECTRICAL_PROTECTION_ACTIONS)
        form.addRow(tr("electrical.action"), self.action_combo)
        self.detail_box.setEnabled(False)
        splitter.addWidget(self.detail_box)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

        for widget, signal in (
            (self.enabled_check, self.enabled_check.toggled),
            (self.setting_spin, self.setting_spin.valueChanged),
            (self.hysteresis_spin, self.hysteresis_spin.valueChanged),
            (self.delay_spin, self.delay_spin.valueChanged),
            (self.action_combo, self.action_combo.currentTextChanged),
        ):
            signal.connect(self._on_detail_changed)

        self.refresh()

    def refresh(self):
        project = self._studio_window._project
        if ensure_electrical_protection_seeded(project):
            project.touch()
            self._studio_window._on_project_changed()

        self._loading = True
        self.tree.clear()
        by_key = {(s.function_id, s.stage_name): s for s in project.electrical_protection_stages}
        category_items = {}
        select_item = None
        for category, function_id, _source, _unit, stage_defs in ELECTRICAL_PROTECTION_CATALOG:
            cat_item = category_items.get(category)
            if cat_item is None:
                cat_item = QTreeWidgetItem([tr(f"electrical.category_{_slug(category)}")])
                f = cat_item.font(0)
                f.setBold(True)
                cat_item.setFont(0, f)
                cat_item.setFlags(cat_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
                self.tree.addTopLevelItem(cat_item)
                category_items[category] = cat_item
            func_item = QTreeWidgetItem([function_id])
            func_item.setFlags(func_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            cat_item.addChild(func_item)
            for stage_name, *_defaults in stage_defs:
                stage = by_key[(function_id, stage_name)]
                stage_item = QTreeWidgetItem([stage_name])
                stage_item.setFlags(stage_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                stage_item.setCheckState(
                    0, Qt.CheckState.Checked if stage.enabled else Qt.CheckState.Unchecked
                )
                stage_item.setData(0, Qt.ItemDataRole.UserRole, (function_id, stage_name))
                func_item.addChild(stage_item)
                if (function_id, stage_name) == self._current_key:
                    select_item = stage_item
        self.tree.expandAll()
        if select_item is not None:
            self.tree.setCurrentItem(select_item)
        else:
            self.detail_box.setEnabled(False)
            self._current_key = None
        self._loading = False

    def _find_stage(self, key):
        project = self._studio_window._project
        for stage in project.electrical_protection_stages:
            if (stage.function_id, stage.stage_name) == key:
                return stage
        return None

    def _catalog_entry(self, function_id):
        for category, fid, source, unit, stage_defs in ELECTRICAL_PROTECTION_CATALOG:
            if fid == function_id:
                return category, source, unit
        return "", "", ""

    def _on_selection_changed(self, current, _previous):
        if current is None:
            return
        key = current.data(0, Qt.ItemDataRole.UserRole)
        if key is None:  # a Category or Function header, not a Stage
            self.detail_box.setEnabled(False)
            self._current_key = None
            return
        stage = self._find_stage(key)
        if stage is None:
            return
        self._current_key = key
        self.detail_box.setEnabled(True)
        _category, source, unit = self._catalog_entry(stage.function_id)
        self._loading = True
        self.enabled_check.setChecked(stage.enabled)
        self.source_label.setText(f"{source} [{unit}]" if unit else source)
        self.setting_spin.setSuffix(f" {unit}" if unit else "")
        self.setting_spin.setValue(stage.setting)
        self.hysteresis_spin.setSuffix(f" {unit}" if unit else "")
        self.hysteresis_spin.setValue(stage.hysteresis)
        self.delay_spin.setValue(stage.delay_ms)
        idx = self.action_combo.findText(stage.action)
        self.action_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._loading = False

    def _on_tree_item_changed(self, item, column):
        if self._loading or column != 0:
            return
        key = item.data(0, Qt.ItemDataRole.UserRole)
        if key is None:
            return
        stage = self._find_stage(key)
        if stage is None:
            return
        stage.enabled = item.checkState(0) == Qt.CheckState.Checked
        if key == self._current_key:
            self._loading = True
            self.enabled_check.setChecked(stage.enabled)
            self._loading = False
        self._studio_window._project.touch()
        self._studio_window._on_project_changed()

    def _on_detail_changed(self, *_args):
        if self._loading or self._current_key is None:
            return
        stage = self._find_stage(self._current_key)
        if stage is None:
            return
        stage.enabled = self.enabled_check.isChecked()
        stage.setting = self.setting_spin.value()
        stage.hysteresis = self.hysteresis_spin.value()
        stage.delay_ms = self.delay_spin.value()
        stage.action = self.action_combo.currentText()
        # Keep the tree's own checkbox in sync without recursing back
        # into _on_tree_item_changed().
        current_item = self.tree.currentItem()
        if current_item is not None:
            self._loading = True
            current_item.setCheckState(
                0, Qt.CheckState.Checked if stage.enabled else Qt.CheckState.Unchecked
            )
            self._loading = False
        self._studio_window._project.touch()
        self._studio_window._on_project_changed()


class ProcessProtectionPanel(QWidget):
    """SPEC's "Nastawy zabezpieczeń" (process side) - a dynamic, user-
    created list (unlike Electrical's fixed catalog), same master/
    detail SHAPE anyway (task: "tu również... na maksa rozbudowujemy",
    read as "the same treatment", not "a smaller one because there's
    less to configure"). Left: table with an Enabled column acting as
    the toggle switch. Right: the selected protection's own point +
    thresholds, field-for-field match to process_protection_manager.
    add_protection()/update_protection()."""

    _COLS = ["enabled", "id", "name"]

    def __init__(self, studio_window, parent=None):
        super().__init__(parent)
        self._studio_window = studio_window
        self._loading = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.table = QTableWidget(0, len(self._COLS))
        self.table.setHorizontalHeaderLabels([tr(f"process.col_{c}") for c in self._COLS])
        _prep_table(self.table)
        _make_column_resizable(self.table, 2, 220)
        self.table.itemChanged.connect(self._on_item_changed)
        self.table.currentCellChanged.connect(self._on_selection_changed)
        splitter.addWidget(self.table)

        self.detail_box = QGroupBox(tr("process.detail_heading"))
        form = QFormLayout(self.detail_box)
        self.point_combo = QComboBox()
        form.addRow(tr("process.point"), self.point_combo)
        self.upper_spin = QDoubleSpinBox()
        self.upper_spin.setRange(-1_000_000.0, 1_000_000.0)
        self.upper_spin.setDecimals(2)
        form.addRow(tr("process.upper_threshold"), self.upper_spin)
        self.lower_spin = QDoubleSpinBox()
        self.lower_spin.setRange(-1_000_000.0, 1_000_000.0)
        self.lower_spin.setDecimals(2)
        form.addRow(tr("process.lower_threshold"), self.lower_spin)
        self.hysteresis_spin = QDoubleSpinBox()
        self.hysteresis_spin.setRange(0.0, 1_000_000.0)
        self.hysteresis_spin.setDecimals(2)
        form.addRow(tr("process.hysteresis"), self.hysteresis_spin)
        self.delay_spin = _seconds_spinbox()
        form.addRow(tr("process.delay_seconds"), self.delay_spin)
        self.detail_box.setEnabled(False)
        splitter.addWidget(self.detail_box)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

        for widget, signal in (
            (self.point_combo, self.point_combo.currentIndexChanged),
            (self.upper_spin, self.upper_spin.valueChanged),
            (self.lower_spin, self.lower_spin.valueChanged),
            (self.hysteresis_spin, self.hysteresis_spin.valueChanged),
            (self.delay_spin, self.delay_spin.valueChanged),
        ):
            signal.connect(self._on_detail_changed)

        self.refresh()

    def refresh(self):
        self._loading = True
        selected_id = self._current_protection_id()
        self.table.setRowCount(0)
        select_row = -1
        for row, protection in enumerate(self._studio_window._project.process_protections):
            self._append_row(protection)
            if protection.id == selected_id:
                select_row = row
        if select_row >= 0:
            self.table.setCurrentCell(select_row, 1)
        else:
            self.detail_box.setEnabled(False)
        self._loading = False

    def _append_row(self, protection: ProcessProtection):
        row = self.table.rowCount()
        self.table.insertRow(row)
        check_item = QTableWidgetItem()
        check_item.setFlags((check_item.flags() | Qt.ItemFlag.ItemIsUserCheckable) & ~Qt.ItemFlag.ItemIsEditable)
        check_item.setCheckState(Qt.CheckState.Checked if protection.enabled else Qt.CheckState.Unchecked)
        self.table.setItem(row, 0, check_item)
        id_item = QTableWidgetItem(protection.id)
        id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, 1, id_item)
        self.table.setItem(row, 2, QTableWidgetItem(protection.name))

    def _current_protection_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 1)
        return item.text() if item is not None else None

    def _find_protection(self, protection_id):
        for protection in self._studio_window._project.process_protections:
            if protection.id == protection_id:
                return protection
        return None

    def select_protection(self, protection_id: str):
        """Task point 6 - validation report navigation target."""
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 1)
            if item is not None and item.text() == protection_id:
                self.table.setCurrentCell(row, 1)
                self.table.scrollToItem(item)
                return

    def add_protection(self):
        project = self._studio_window._project
        existing_ids = {p.id for p in project.process_protections}
        new_id = _next_unique(existing_ids, "PP")
        project.process_protections.append(ProcessProtection(id=new_id, name=tr("process.default_name", id=new_id)))
        project.touch()
        self.refresh()
        self._studio_window._on_project_changed()

    def remove_selected_protection(self):
        protection_id = self._current_protection_id()
        if protection_id is None:
            return
        project = self._studio_window._project
        project.process_protections = [p for p in project.process_protections if p.id != protection_id]
        project.touch()
        self.refresh()
        self._studio_window._on_project_changed()

    def _on_item_changed(self, item):
        if self._loading:
            return
        row = item.row()
        id_item = self.table.item(row, 1)
        if id_item is None:
            return
        protection = self._find_protection(id_item.text())
        if protection is None:
            return
        if item.column() == 0:
            protection.enabled = item.checkState() == Qt.CheckState.Checked
            if protection.id == self._current_protection_id():
                self._loading = True
                self.detail_box.setEnabled(True)
                self._loading = False
        elif item.column() == 2:
            protection.name = item.text()
        self._studio_window._project.touch()
        self._studio_window._on_project_changed()

    def _on_selection_changed(self, current_row, _current_col, _prev_row, _prev_col):
        if self._loading or current_row < 0:
            return
        protection_id = self._current_protection_id()
        protection = self._find_protection(protection_id)
        if protection is None:
            self.detail_box.setEnabled(False)
            return
        self.detail_box.setEnabled(True)
        ai_points = points_of_kind(self._studio_window._project, "AI")
        self._loading = True
        self.point_combo.clear()
        for point in ai_points:
            label = point.address if not point.description else f"{point.address} — {point.description}"
            self.point_combo.addItem(label, point.address)
        idx = self.point_combo.findData(protection.analog_tag)
        self.point_combo.setCurrentIndex(idx if idx >= 0 else -1)
        self.upper_spin.setValue(protection.upper_threshold)
        self.lower_spin.setValue(protection.lower_threshold)
        self.hysteresis_spin.setValue(protection.hysteresis)
        self.delay_spin.setValue(protection.delay_seconds)
        self._loading = False

    def _on_detail_changed(self, *_args):
        if self._loading:
            return
        protection_id = self._current_protection_id()
        protection = self._find_protection(protection_id)
        if protection is None:
            return
        protection.analog_tag = self.point_combo.currentData() or ""
        protection.upper_threshold = self.upper_spin.value()
        protection.lower_threshold = self.lower_spin.value()
        protection.hysteresis = self.hysteresis_spin.value()
        protection.delay_seconds = self.delay_spin.value()
        self._studio_window._project.touch()
        self._studio_window._on_project_changed()


class ControllerPanel(QWidget):
    """"Połączenie i podgląd" (STEROWNIK) - Studio <-> a real EPW-OS
    controller, over its existing REST API (SPEC_PROJEKT_EPW.md: "Studio
    łączy się ze sterownikiem przez istniejące REST API [...] ten sam
    mechanizm co dla HAOS"). Host/token live in QSettings, NOT in
    project.epw - a bearer token is a per-operator secret (runtime's own
    api_auth.py: "token authenticates a LEVEL"), not project data meant
    to be shared or committed alongside a project file. A flagged
    engineering call, not something the contract states outright.

    "Testuj połączenie" and "Pobierz podgląd tagów" are REAL - GET
    /api/v1/health and /api/v1/tags already exist in runtime/epw_os/
    backend/api.py and this panel calls them for real (stdlib
    urllib.request only - GRANICE: no new dependency for one HTTP GET).

    "Wyślij do urządzenia"/"Zgraj z urządzenia" (task's own two options)
    are honestly INCOMPLETE: verified empirically - that same api.py has
    ZERO endpoints for a project config upload/download or a revision
    check (the exact mechanism SPEC_PROJEKT_EPW.md's own "Wersjonowanie"
    section describes: "przed wgraniem projektu [...] odczytać revision
    z urządzenia [...] rozjazd = ZATRZYMAĆ SIĘ"). Clicking either button
    explains exactly what's missing on the runtime side - GRANICE
    forbids touching runtime/ from here to invent one, and a button that
    silently pretends to sync is the exact facade this whole session
    avoids."""

    _SETTINGS_HOST = "controller/host"
    _SETTINGS_TOKEN = "controller/token"

    def __init__(self, studio_window, parent=None):
        super().__init__(parent)
        self._studio_window = studio_window

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        conn_box = QGroupBox(tr("controller.connection_heading"))
        form = QFormLayout(conn_box)
        self.host_edit = QLineEdit()
        self.host_edit.setPlaceholderText("http://192.168.1.50:8000")
        form.addRow(tr("controller.host"), self.host_edit)
        self.token_edit = QLineEdit()
        self.token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow(tr("controller.token"), self.token_edit)
        self.host_edit.editingFinished.connect(self._save_connection_settings)
        self.token_edit.editingFinished.connect(self._save_connection_settings)
        layout.addWidget(conn_box)

        test_row = QHBoxLayout()
        self.test_button = QPushButton(tr("controller.test_connection"))
        self.test_button.clicked.connect(self._test_connection)
        test_row.addWidget(self.test_button)
        self.status_label = QLabel(tr("controller.status_unknown"))
        test_row.addWidget(self.status_label, 1)
        layout.addLayout(test_row)

        sync_box = QGroupBox(tr("controller.sync_heading"))
        sync_layout = QHBoxLayout(sync_box)
        self.send_button = QPushButton(tr("controller.send_to_device"))
        self.send_button.clicked.connect(self._send_to_device)
        sync_layout.addWidget(self.send_button)
        self.receive_button = QPushButton(tr("controller.receive_from_device"))
        self.receive_button.clicked.connect(self._receive_from_device)
        sync_layout.addWidget(self.receive_button)
        sync_layout.addStretch(1)
        layout.addWidget(sync_box)

        preview_box = QGroupBox(tr("controller.preview_heading"))
        preview_layout = QVBoxLayout(preview_box)
        self.preview_button = QPushButton(tr("controller.fetch_tags"))
        self.preview_button.clicked.connect(self._fetch_tag_preview)
        preview_layout.addWidget(self.preview_button)
        self.preview_table = QTableWidget(0, 3)
        self.preview_table.setHorizontalHeaderLabels(
            [tr("controller.col_tag"), tr("controller.col_value"), tr("controller.col_quality")]
        )
        _prep_table(self.preview_table)
        _make_column_resizable(self.preview_table, 0, 260)
        preview_layout.addWidget(self.preview_table)
        layout.addWidget(preview_box, 1)

        self._load_connection_settings()

    def _load_connection_settings(self):
        settings = self._studio_window.settings
        self.host_edit.setText(settings.value(self._SETTINGS_HOST, ""))
        self.token_edit.setText(settings.value(self._SETTINGS_TOKEN, ""))

    def _save_connection_settings(self):
        settings = self._studio_window.settings
        settings.setValue(self._SETTINGS_HOST, self.host_edit.text().strip())
        settings.setValue(self._SETTINGS_TOKEN, self.token_edit.text())

    def _request(self, path: str, timeout: float = 4.0):
        """One GET against the configured host, stdlib only. Returns
        (True, parsed_json) or (False, error_message) - never raises,
        same "a connectivity problem is data, not a crash" stance every
        other network-adjacent feature in this codebase already takes."""
        import json as _json
        import urllib.error
        import urllib.request

        host = self.host_edit.text().strip().rstrip("/")
        if not host:
            return False, tr("controller.error_no_host")
        url = f"{host}{path}"
        headers = {}
        token = self.token_edit.text().strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read().decode("utf-8")
            return True, _json.loads(body) if body else {}
        except urllib.error.HTTPError as e:
            return False, tr("controller.error_http", code=e.code, reason=e.reason)
        except urllib.error.URLError as e:
            return False, tr("controller.error_connection", reason=str(e.reason))
        except Exception as e:  # noqa: BLE001 - any failure here is "show it", not a Studio crash
            return False, str(e)

    def _test_connection(self):
        self.status_label.setText(tr("controller.status_testing"))
        QApplication.processEvents()
        ok, result = self._request("/api/v1/health")
        if ok:
            self.status_label.setText(tr("controller.status_ok"))
        else:
            self.status_label.setText(tr("controller.status_failed", reason=result))

    def _fetch_tag_preview(self):
        ok, result = self._request("/api/v1/tags")
        if not ok:
            QMessageBox.warning(self, tr("controller.preview_heading"), result)
            return
        self.preview_table.setRowCount(0)
        tags = result if isinstance(result, list) else result.get("tags", [])
        for tag in tags:
            row = self.preview_table.rowCount()
            self.preview_table.insertRow(row)
            self.preview_table.setItem(row, 0, QTableWidgetItem(str(tag.get("name", ""))))
            self.preview_table.setItem(row, 1, QTableWidgetItem(str(tag.get("value", ""))))
            self.preview_table.setItem(row, 2, QTableWidgetItem(str(tag.get("quality", ""))))

    def _send_to_device(self):
        QMessageBox.information(self, tr("controller.send_to_device"), tr("controller.not_implemented_send"))

    def _receive_from_device(self):
        QMessageBox.information(self, tr("controller.receive_from_device"), tr("controller.not_implemented_receive"))


class HelpPanel(QWidget):
    """"Dział help pełny" - a real, browsable topic tree + a Markdown
    viewer, one per Studio panel (see studio/shell/help/generate_help.py
    for the actual content and why it's original to Studio, not copied
    from runtime/epw_os/help/'s own 164 files - those document a
    DIFFERENT program's own screens). Topic list/order comes from
    studio/shell/help/_manifest.py, generated alongside the .md content
    so the two can never disagree. Language follows Studio's own
    current language (get_language()) - switching language in
    Ustawienia switches which folder this reads from next time it's
    opened, same as every other tr()'d string in Studio."""

    def __init__(self, studio_window, parent=None):
        super().__init__(parent)
        self._studio_window = studio_window

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.topic_list = QListWidget()
        self.topic_list.setFixedWidth(240)
        self.topic_list.currentRowChanged.connect(self._on_topic_selected)
        splitter.addWidget(self.topic_list)

        self.viewer = QTextBrowser()
        self.viewer.setOpenExternalLinks(False)
        splitter.addWidget(self.viewer)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

        self._topics = []
        self.refresh()

    def refresh(self):
        from studio.shell.i18n import get_language
        from studio.shell.help._manifest import TOPICS

        current_key = self._topics[self.topic_list.currentRow()][0] if self._topics else None
        self._topics = TOPICS
        self._lang = get_language()

        self.topic_list.blockSignals(True)
        self.topic_list.clear()
        select_row = 0
        for i, (key, title_pl, title_en) in enumerate(self._topics):
            self.topic_list.addItem(title_pl if self._lang == "pl" else title_en)
            if key == current_key:
                select_row = i
        self.topic_list.blockSignals(False)
        self.topic_list.setCurrentRow(select_row)
        self._on_topic_selected(select_row)

    def _on_topic_selected(self, row):
        if row < 0 or row >= len(self._topics):
            self.viewer.setMarkdown("")
            return
        key, _title_pl, _title_en = self._topics[row]
        self.viewer.setMarkdown(load_help_topic_markdown(key, self._lang))

    def select_topic(self, key: str):
        """Task 5.3 (pomoc kontekstowa, F1) - jumps straight to `key`
        instead of making the caller know this panel's own row-index
        bookkeeping. A silent no-op for an unknown key (same "don't
        crash over a lookup miss" stance _on_topic_selected() above
        already has for a missing .md file) rather than raising -
        _HELP_TOPIC_BY_TREE_KEY in main_window.py is a hand-maintained
        map that could in principle name a topic not in TOPICS."""
        for row, (topic_key, _pl, _en) in enumerate(self._topics):
            if topic_key == key:
                self.topic_list.setCurrentRow(row)
                return


def load_help_topic_markdown(key: str, lang: str) -> str:
    """Shared by HelpPanel and AboutDialog (task 5.1's own "about" topic
    needs the exact same load-a-.md-file mechanism, not a second one) -
    reads studio/shell/help/<lang>/<key>.md and substitutes `{version}`
    where present (runtime/epw_os/gui/widgets/about_dialog.py's own
    HelpContentStore.load_topic_markdown() does the same for its "about"
    topic - mirrored here, not reinvented). A stray brace in some future
    topic's own prose would make str.format() raise - caught and
    returned unformatted rather than crashing the whole panel over it."""
    help_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "help")
    path = os.path.join(help_dir, lang, f"{key}.md")
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return f"*(brak pliku pomocy: {path})*"
    try:
        from studio.shell.version import STUDIO_VERSION
        return text.format(version=STUDIO_VERSION)
    except (KeyError, IndexError):
        return text


class AboutDialog(QDialog):
    """"Pomoc → O programie" (task 5.1) - same structure as runtime/
    epw_os/gui/widgets/about_dialog.py's own AboutDialog (read before
    writing this one, per the task's own instruction): logo, bold app
    name, version line, a scrollable Markdown body (the "about" help
    topic - same load_help_topic_markdown() HelpPanel itself uses, not
    a second mechanism), a Close button. Logo is the REAL, full
    runtime/epw_os/resources/about_logo.png (read-only) at the same
    scale-down-never-up, null-safe stance that dialog already
    established - not the cropped "EPW" plaque studio/shell/identity/
    uses for the app/file icons (those are small-size derivatives;
    this dialog has room for the real thing, same as runtime's own)."""

    _LOGO_MAX_WIDTH = 320
    _LOGO_MAX_HEIGHT = 160

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("about.title"))
        self.setModal(True)
        self.setMinimumSize(420, 480)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        logo_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "runtime", "epw_os", "resources", "about_logo.png",
        )
        pixmap = QPixmap(logo_path) if os.path.isfile(logo_path) else None
        if pixmap is not None and not pixmap.isNull():
            logo_label = QLabel()
            scaled = pixmap.scaled(
                self._LOGO_MAX_WIDTH, self._LOGO_MAX_HEIGHT,
                Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation,
            )
            logo_label.setPixmap(scaled)
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(logo_label)
        # else: no logo file (or unreadable) - the dialog still works,
        # just without the image, same as runtime's own.

        header = QLabel(tr("app.title"))
        f = header.font()
        f.setBold(True)
        f.setPointSize(f.pointSize() + 4)
        header.setFont(f)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        from studio.shell.version import STUDIO_VERSION
        version_label = QLabel(f"{tr('about.version_label')}: {STUDIO_VERSION}")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_label)

        from studio.shell.i18n import get_language
        text_browser = QTextBrowser()
        text_browser.setOpenExternalLinks(False)
        text_browser.setMarkdown(load_help_topic_markdown("about", get_language()))
        layout.addWidget(text_browser, 1)

        close_button = QPushButton(tr("about.btn_close"))
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignCenter)


@dataclass
class ValidationIssue:
    """Task point 6 ("Sprawdź projekt") - one row of validate_project()'s
    report. `target`/`selector`/`arg` are how "klik przenosi do miejsca
    problemu" (not a one-sentence modal) actually works: `target` is a
    small, main_window-independent kind string (see validate_project()'s
    own docstring for the full list) that main_window.py's own
    _navigate_to_validation_issue() maps to one of its own _TREE_ITEM_*
    constants + panel - project_panels.py itself never imports
    main_window (keeps this module importable standalone, same
    "no upward import" stance every panel class here already keeps by
    only ever reaching `self._studio_window`, never the module itself)."""

    severity: str  # "error" | "warning"
    message: str
    target: str = ""
    selector: str = ""
    arg: str = ""


def validate_project(project) -> list:
    """Task point 6 - the seven checks verbatim from the task text,
    each producing zero or more ValidationIssue rows instead of a
    single modal sentence. ERROR = the project is not internally
    consistent (a reference points at nothing, or two things claim the
    same resource); WARNING = the project still hangs together but has
    an omission worth a human's attention (a location typo, orphaned-
    but-not-deleted module data) - the same "warn, never delete" stance
    _module_has_data()/ModuleCompositionPanel._on_toggled() already
    take for the module case is exactly check 7 below, reused, not
    reimplemented.

    `target` values, matched by main_window._navigate_to_validation_
    issue(): "devices", "points", "lines", "process_protection",
    "modules"."""
    issues = []
    point_addresses = {p.address for p in project.points}
    card_ids = {c.id for c in project.cards}
    location_codes = {loc.code for loc in project.locations}

    def _card_id_of(address):
        return address.split(".", 1)[0] if "." in address else address

    # 1) "aparat wskazuje punkt, który nie istnieje"
    # 2) "aparat wskazuje punkt z karty, która została usunięta"
    # 3) "dwa aparaty na tym samym punkcie"
    address_owners = {}
    for device in project.devices:
        for address in list(device.feedback) + list(device.command):
            address_owners.setdefault(address, []).append(device.id)
            if address not in point_addresses:
                issues.append(ValidationIssue(
                    "error",
                    tr("validation.msg_device_missing_point", device=device.id, address=address),
                    "devices", "select_device", device.id,
                ))
            elif _card_id_of(address) not in card_ids:
                issues.append(ValidationIssue(
                    "error",
                    tr(
                        "validation.msg_device_point_deleted_card",
                        device=device.id, address=address, card=_card_id_of(address),
                    ),
                    "devices", "select_device", device.id,
                ))
    for address, owners in address_owners.items():
        unique_owners = sorted(set(owners))
        if len(unique_owners) > 1:
            issues.append(ValidationIssue(
                "error",
                tr("validation.msg_point_double_owned", address=address, devices=", ".join(unique_owners)),
                "devices", "select_device", unique_owners[0],
            ))

    # 4) "punkt z lokalizacją, której nie ma na liście"
    for point in project.points:
        if point.location and point.location not in location_codes:
            issues.append(ValidationIssue(
                "warning",
                tr("validation.msg_point_unknown_location", address=point.address, location=point.location),
                "points", "select_address", point.address,
            ))

    # 5) "linia dozorowa wskazująca nieistniejący punkt"
    for line in project.lines:
        if line.tag and line.tag not in point_addresses:
            issues.append(ValidationIssue(
                "error",
                tr("validation.msg_line_missing_point", line=line.id, address=line.tag),
                "lines", "select_line", line.id,
            ))

    # 6) "zabezpieczenie procesowe wskazujące nieistniejący punkt AI" -
    # covers BOTH "nie istnieje" (missing outright) and "istnieje, ale
    # to nie jest AI" (wrong kind) - points_of_kind() is the same
    # DI/AI-only lookup LineConfigDialog's own point picker already uses.
    ai_addresses = {p.address for p in points_of_kind(project, "AI")}
    for pp in project.process_protections:
        if not pp.analog_tag:
            continue
        if pp.analog_tag not in point_addresses:
            issues.append(ValidationIssue(
                "error",
                tr("validation.msg_process_missing_point", protection=pp.id, address=pp.analog_tag),
                "process_protection", "select_protection", pp.id,
            ))
        elif pp.analog_tag not in ai_addresses:
            issues.append(ValidationIssue(
                "error",
                tr("validation.msg_process_not_ai_point", protection=pp.id, address=pp.analog_tag),
                "process_protection", "select_protection", pp.id,
            ))

    # 7) "moduł ma dane, ale nie jest w składzie urządzenia"
    for feature_id in MODULE_IDS:
        if feature_id not in project.modules and _module_has_data(project, feature_id):
            entry = _module_entry(feature_id)
            from studio.shell.i18n import get_language
            name = (entry[1] if get_language() == "pl" else entry[2]) if entry else feature_id
            issues.append(ValidationIssue(
                "warning",
                tr("validation.msg_module_has_orphan_data", module=name),
                "modules", "select_module", feature_id,
            ))

    return issues


class ValidationReportDialog(QDialog):
    """Task point 6 - "Wynik: lista z podziałem BŁĄD/OSTRZEŻENIE, klik
    przenosi do miejsca problemu. Nie modalne okno z jednym zdaniem."
    Two always-visible sections (not tabs - the task's own complaint is
    about a single terse sentence, not about section count), non-modal
    (setModal(False)) so it can stay open while the user fixes things
    in the panel underneath and re-runs "Sprawdź projekt" to check."""

    def __init__(self, issues, on_navigate, parent=None):
        super().__init__(parent)
        self._on_navigate = on_navigate
        self.setWindowTitle(tr("validation.dialog_title"))
        self.setModal(False)
        self.resize(720, 480)

        errors = [i for i in issues if i.severity == "error"]
        warnings = [i for i in issues if i.severity == "warning"]

        layout = QVBoxLayout(self)

        summary = QLabel(tr("validation.summary", errors=len(errors), warnings=len(warnings)))
        bold_font = summary.font()
        bold_font.setBold(True)
        summary.setFont(bold_font)
        layout.addWidget(summary)

        if not issues:
            layout.addWidget(QLabel(tr("validation.none_found")))
        else:
            layout.addWidget(QLabel(tr("validation.hint_double_click")))
            if errors:
                layout.addWidget(self._build_section(tr("validation.section_errors"), errors), 1)
            if warnings:
                layout.addWidget(self._build_section(tr("validation.section_warnings"), warnings), 1)

        close_button = QPushButton(tr("validation.close"))
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignRight)

    def _build_section(self, title: str, section_issues) -> QGroupBox:
        box = QGroupBox(f"{title} ({len(section_issues)})")
        box_layout = QVBoxLayout(box)
        listing = QListWidget()
        for issue in section_issues:
            item = QListWidgetItem(issue.message)
            item.setData(Qt.ItemDataRole.UserRole, issue)
            listing.addItem(item)
        listing.itemDoubleClicked.connect(self._on_item_double_clicked)
        box_layout.addWidget(listing)
        return box

    def _on_item_double_clicked(self, item):
        issue = item.data(Qt.ItemDataRole.UserRole)
        if issue is not None and self._on_navigate is not None:
            self._on_navigate(issue)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


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
    # No setSectionResizeMode(..., Stretch) anywhere in this module
    # (fixed live bug, real screenshot: user could not drag-resize a
    # Stretch column at all - Qt's own ResizeMode.Stretch docs: "the
    # section is not user-resizable", not merely "auto-sized"). Every
    # table's one naturally-wide column instead gets a sensible INITIAL
    # width via _make_column_resizable() below, staying fully draggable
    # afterward - task's own "każda tabela musi mieć możliwość regulacji
    # szerokości kolumny [...] mowa tu o wszystkich działach".


def _make_column_resizable(table: QTableWidget, column: int, initial_width: int):
    """Interactive (Qt's own default) is what actually allows the user
    to drag a column's border - explicitly re-asserted here (not just
    left at the default) so a future column added to one of these
    tables doesn't silently inherit some other resize mode from a
    stylesheet or a Qt version's own changed default."""
    table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeMode.Interactive)
    table.setColumnWidth(column, initial_width)


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
