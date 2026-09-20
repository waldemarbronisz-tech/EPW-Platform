"""Task "edytor DI/DO/AI" - real panels for three of the tree branches
task 1.4 (main_window.py's own _INACTIVE_CONFIG_CHILDREN) deliberately
left as placeholders: "Informacje o projekcie", "Karty wejść/wyjść",
"Rejestr punktów". SPEC_PROJEKT_EPW.md's own "Kolejność wdrożenia" step
2 is exactly this - "Rejestr punktów w Studio — karty rodzą punkty,
opisy" - built on top of step 1 (project_format.py, already done).

Scope, stated plainly because it matters: this makes the point registry
real WITHIN Studio's own Project object. Update (task "migracja
adresacji", step 5 mentioned below): that step has since happened -
Logic Studio's device_model.py now generates the identical
`<card>.<KIND>.<channel>` grammar this module does (both, along with
runtime and Studio here, go through shared/addressing.py's
format_address()/parse_address() - see that module's own docstring),
not the old "ELA01.DI01" shape this comment used to describe. The
"bridge vs migration" question ADDRESSING_INVENTORY.md raised is
resolved: migration, no bridge, no old-name mapping.

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
import csv
import io
import json
import os
import re
from dataclasses import dataclass

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox, QFileDialog,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
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

from shared.addressing import format_address, parse_address, try_parse_address
from studio.shell.i18n import tr
from studio.shell.project_format import (
    effective_location,
    Card, Device, ELECTRICAL_PROTECTION_ACTIONS, ElectricalProtectionStage, IntrusionUser, Line,
    LineInputMode, LineParametrization, LineType, Location, MqttConfig, NORMAL_STATE_NC, NORMAL_STATE_NO,
    Point, PowerSupervision, ProcessProtection, ProjectFormatError, Sounder, Zone, default_value_windows,
    apply_settings_snapshot, load_project, settings_diff, settings_hash, settings_snapshot,
)
from studio.shell.site_format import LINK_TAG_RE, OBJECT_LINK_MARK, link_type_for, suggest_link_tag
from pathlib import Path

CHANNEL_KINDS = ["DI", "DO", "AI", "AO"]
_ANALOG_KINDS = {"AI", "AO"}
DEVICE_BEHAVIORS = ["SWITCHED", "SIGNAL", "MEASURED", "MODULATED", "SELECTOR"]
# Task "wyłącznik jednocewkowy bistabilny" - see project_format.Device.
# command_style for what each means; PULSE and PULSE_TOGGLE need pulse_ms.
COMMAND_STYLES = ["MAINTAINED", "PULSE", "PULSE_TOGGLE"]
_PULSED_STYLES = {"PULSE", "PULSE_TOGGLE"}

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
_DIFF_BG = QColor("#FFF1B8")   # a setting that differs between Studio and the controller
_LIVE_BG = QColor("#E4F5E4")   # a live value of GOOD quality
_LIVE_BAD_BG = QColor("#FFE0B3")   # a live value whose quality is not GOOD
_FORCED_BG = QColor("#FFB3B3")   # a forced tag - red, always visible (SPEC "Wymuszanie stanów")
_LOCATION_CODE_RE = re.compile(r"^[A-Z0-9]+$")
# User report #3: "karta bez adresu jednostki nie odezwie się na
# magistrali [...] pusty adres ma być widocznym brakiem, nie ciszą" - a
# blank Modbus-address cell looks identical to a disabled/read-only one
# (it IS editable, see _append_card_row()'s own item - nothing disables
# it), so an empty value needs a color, not just empty text, to read as
# "missing" rather than "nothing to see here".
_MISSING_MODBUS_BG = QColor("#FDE2E2")

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
    """`<id>.<kind>.<channel>` for every (kind, channel) the card's own
    channel_kinds has - the SPEC's own card-relative addressing rule
    (already the same shape Synoptic's own ChannelAddress uses,
    DeviceSchema.ts's own docstring: 'CARD.KIND.CHANNEL'). One card can
    have more than one kind (task follow-up, user report: "karta ELA1
    ma DI oraz AI") - every kind contributes its OWN channel range under
    the same id, KIND being its own address segment already. Built
    through shared/addressing.py's own format_address() rather than a
    hand-rolled f-string - task "migracja adresacji" etap-3 follow-up
    ("jedna funkcja walidująca, nie trzy kopie"): runtime and Logic
    Studio already build every address this way, so this was the one
    remaining Python address-generation site with its own independent
    copy of the same three-segment rule."""
    return [
        format_address(card.id, kind, n)
        for kind, channels in card.channel_kinds.items()
        for n in range(1, channels + 1)
    ]


def points_for_card(project, card: Card):
    addrs = set(_card_channel_addresses(card))
    return [p for p in project.points if p.address in addrs]


def _address_sort_key(address: str):
    """(card, kind, channel:int) for sorting a list of point addresses -
    user report: "Rejestr punktów pokazuje DI.1, DI.10, DI.11 ... DI.2" -
    plain `sorted(..., key=lambda p: p.address)` sorts the CHANNEL as
    text, not as a number, so "10" sorts before "2". Every point address
    in this program is machine-generated by _card_channel_addresses()
    (format_address()), never hand-typed, so parse_address() is never
    expected to fail here; letting it raise on a genuinely malformed
    address is the same "loud, not silent" stance the rest of this
    task's own addressing work already takes, not a new risk."""
    return parse_address(address)


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
    wanted_set = set(wanted)
    # Every kind this card has, its own prefix - a card with several
    # kinds (task follow-up: "karta ELA1 ma DI oraz AI") owns points
    # under ALL of them, not just one. str.startswith() takes a tuple of
    # prefixes directly.
    prefixes = tuple(f"{card.id}.{kind}." for kind in card.channel_kinds)
    existing_addresses = {p.address for p in project.points}
    # Drop points whose address belongs to this card but is no longer
    # in range (a kind's channel count shrank, or a kind was removed).
    project.points = [
        p for p in project.points
        if not (p.address.startswith(prefixes) and p.address not in wanted_set)
    ]
    for addr in wanted:
        if addr not in existing_addresses:
            project.points.append(Point(address=addr))
    project.points.sort(key=lambda p: _address_sort_key(p.address))


def remove_points_for_card(project, card: Card):
    prefixes = tuple(f"{card.id}.{kind}." for kind in card.channel_kinds)
    project.points = [p for p in project.points if not p.address.startswith(prefixes)]


# -- Synoptic bridge field-name mapping ------------------------------------
# Synoptic's own DeviceSchema.ts: CardEntry{id,model,channelKind,
# channelCount}, LocationEntry{code,description} - same two lists as
# Card/Location here, different field names on the Card side only.
# main_window.py's _sync_device_registry_with_synoptic() is the only
# caller; kept here (not in synoptic_panel.py, which stays a thin JS
# bridge with no knowledge of Studio's own dataclasses).

def card_to_synoptic_dicts(card: Card) -> list:
    """One CardEntry dict per (kind, channels) pair a card has -
    Synoptic's own DeviceSchema.ts has no multi-kind-per-entry concept,
    nor any reason to: it never reads Modbus/location, the two fields
    channel_kinds exists to stop duplicating in the first place (see
    Card's own docstring). A Studio card with several kinds (task
    follow-up, user report: "karta ELA1 ma DI oraz AI") is flattened to
    several CardEntry dicts sharing an id here - exactly the shape
    Synoptic's own validateDeviceRegistry/validateChannelAddress
    (DeviceValidation.ts) already treat as normal, not a conflict."""
    return [
        {"id": card.id, "model": card.model, "channelKind": kind, "channelCount": channels}
        for kind, channels in card.channel_kinds.items()
    ]


def cards_from_synoptic_dicts(entries: list) -> list:
    """Inverse of card_to_synoptic_dicts() - COLLAPSES Synoptic's flat,
    one-CardEntry-per-kind list back into Studio's own one-row-per-
    physical-module Card list, grouped by id (first-seen order).
    modbus_unit_id/location have no Synoptic-side equivalent, so a
    collapsed Card never sets them - see this function's only caller,
    main_window.py's _sync_device_registry_with_synoptic(), for how a
    newly-pulled-in id is handled."""
    order = []
    channel_kinds_by_id = {}
    model_by_id = {}
    for entry in entries:
        card_id = entry.get("id")
        if not card_id:
            continue
        kind = entry.get("channelKind") or CHANNEL_KINDS[0]
        try:
            channels = int(entry.get("channelCount") or 0)
        except (TypeError, ValueError):
            channels = 0
        if card_id not in channel_kinds_by_id:
            order.append(card_id)
            channel_kinds_by_id[card_id] = {}
            model_by_id[card_id] = entry.get("model", "")
        channel_kinds_by_id[card_id][kind] = channels
    return [
        Card(id=card_id, model=model_by_id[card_id], channel_kinds=channel_kinds_by_id[card_id])
        for card_id in order
    ]


def location_to_synoptic_dict(location: Location) -> dict:
    return {"code": location.code, "description": location.description}


def location_from_synoptic_dict(data: dict) -> Location:
    return Location(code=data["code"], description=data.get("description", ""))


# -- apparatuses (punkt 2 / luka 7: "unify the two apparatus registries") --
# Studio's Device is the SPEC's flat shape (feedback[0] = the CLOSED
# contact, command[0] = CLOSE, command[1] = OPEN, commandStyle/pulseMs);
# Synoptic's DeviceSchema.ts is the per-behavior form (diClosed/diOpen/
# doClose/doOpen/pulseMs...). The two say the same thing about the same
# apparatus, so - like cards and locations above - one registry is bridged
# ADD-ONLY into the other in both directions. Studio has no designation/
# name/unit of its own, so a device it pushes gets the IEC-style
# designation from its id ("KOT_KM1" -> "-KM1") and its id as the name;
# Synoptic keeps its own richer fields for devices it already has, since
# the bridge never overwrites.

_DEFAULT_DEVICE_KIND = {"SWITCHED": "contactor", "SIGNAL": "signal", "MEASURED": "sensor",
                        "MODULATED": "actuator", "SELECTOR": "selector"}


def device_designation(device_id: str) -> str:
    """"KOT_KM1" -> "-KM1", "KM1" -> "-KM1" - the designation Synoptic
    draws next to the symbol (IEC 81346 minus + the part after the
    location prefix), and what apparatus.bind_roles_from_screens() on
    the runtime side reads back."""
    suffix = device_id.split("_", 1)[1] if "_" in device_id else device_id
    return "-" + suffix if suffix else ""


def device_to_synoptic_dict(device: Device) -> dict:
    feedback = [a for a in device.feedback if a]
    command = [a for a in device.command if a]
    out = {
        "id": device.id,
        "designation": device_designation(device.id),
        "name": device.id,
        "behavior": device.behavior,
        "kind": device.kind or _DEFAULT_DEVICE_KIND.get(device.behavior, "generic"),
        "publishToHa": False,
    }
    if device.behavior == "SWITCHED":
        fb = {"mode": "NONE"}
        if len(feedback) >= 2:
            fb = {"mode": "DUAL", "diClosed": feedback[0], "diOpen": feedback[1]}
        elif len(feedback) == 1:
            fb = {"mode": "SINGLE", "diClosed": feedback[0]}
        cmd = {"outputCount": 2 if len(command) >= 2 else 1,
               "style": device.command_style if device.command_style in COMMAND_STYLES else COMMAND_STYLES[0],
               "doClose": command[0] if command else ""}
        if len(command) >= 2:
            cmd["doOpen"] = command[1]
        if cmd["style"] in _PULSED_STYLES:
            cmd["pulseMs"] = int(device.pulse_ms or 0)
        supervision = dict(device.supervision)
        supervision.setdefault("confirmTimeoutMs", 1000)
        supervision.setdefault("discrepancyAlarm", False)
        safe_state = dict(device.safe_state)
        safe_state.setdefault("onStartup", "NO_CHANGE")
        safe_state.setdefault("onLinkLoss", "NO_CHANGE")
        out.update({"feedback": fb, "command": cmd, "supervision": supervision, "safeState": safe_state,
                    "switchCounter": False})
    elif device.behavior == "SIGNAL":
        out.update({"feedback": {"di": feedback[0] if feedback else "", "invert": False},
                    "alarmState": "HIGH", "debounceMs": 50})
    elif device.behavior == "MEASURED":
        out.update({"input": feedback[0] if feedback else "", "unit": "", "rangeMin": 0, "rangeMax": 100,
                    "format": "0.0", "deadband": 0})
    elif device.behavior == "MODULATED":
        out.update({"setpointOutput": command[0] if command else "", "unit": "", "rangeMin": 0,
                    "rangeMax": 100, "startupValue": 0, "safeValue": 0})
        if feedback:
            out["feedbackInput"] = feedback[0]
    elif device.behavior == "SELECTOR":
        positions = [{"name": str(n), "feedback": address} for n, address in enumerate(feedback, start=1)]
        while len(positions) < 2:
            positions.append({"name": str(len(positions) + 1)})
        out["positions"] = positions
    return out


def device_from_synoptic_dict(data: dict) -> Device:
    """Inverse of device_to_synoptic_dict() for what Studio's Device holds;
    designation/name/unit/ranges/alarm levels stay Synoptic's own."""
    behavior = data.get("behavior") or DEVICE_BEHAVIORS[0]
    feedback, command = [], []
    supervision, safe_state = {}, {}
    command_style, pulse_ms = COMMAND_STYLES[0], 0
    if behavior == "SWITCHED":
        fb = data.get("feedback") or {}
        feedback = [a for a in (fb.get("diClosed"), fb.get("diOpen")) if a]
        cmd = data.get("command") or {}
        command = [a for a in (cmd.get("doClose"), cmd.get("doOpen")) if a]
        if cmd.get("style") in COMMAND_STYLES:
            command_style = cmd["style"]
        try:
            pulse_ms = int(cmd.get("pulseMs") or 0) if command_style in _PULSED_STYLES else 0
        except (TypeError, ValueError):
            pulse_ms = 0
        supervision = dict(data.get("supervision") or {})
        safe_state = dict(data.get("safeState") or {})
    elif behavior == "SIGNAL":
        di = (data.get("feedback") or {}).get("di")
        feedback = [di] if di else []
    elif behavior == "MEASURED":
        feedback = [data["input"]] if data.get("input") else []
    elif behavior == "MODULATED":
        feedback = [data["feedbackInput"]] if data.get("feedbackInput") else []
        command = [data["setpointOutput"]] if data.get("setpointOutput") else []
    elif behavior == "SELECTOR":
        feedback = [p.get("feedback") for p in (data.get("positions") or []) if isinstance(p, dict) and p.get("feedback")]
    return Device(id=data["id"], behavior=behavior, kind=data.get("kind", ""), feedback=feedback, command=command,
                  supervision=supervision, safe_state=safe_state, command_style=command_style, pulse_ms=pulse_ms)


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


# User report 3.4: never a real location code (SPEC's own code charset is
# A-Z/0-9, _LOCATION_CODE_RE) or "" (the explicit-blank override), so it
# can be a QComboBox item's userData without ever colliding with one.
_INHERIT_LOCATION_SENTINEL = "__inherit__"


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


class _ChannelKindsEditor(QWidget):
    """One card row's "which channel kinds does it have, and how many
    of each" - task follow-up, user report: "karta ELA1 ma DI oraz AI".
    A checkbox per kind (DI/DO/AI/AO), each revealing its own channel-
    count spinbox only once checked. Replaces the old single "kind"
    combo + "channels" number pair: a physical module (an ELA card with
    both digital and analog inputs, say) is one Card row with several
    kinds now, not two rows sharing an id (that earlier shape forced
    modbus_unit_id/location to be entered twice, kept in sync by hand,
    for no reason the address grammar - KIND already its own segment -
    ever required). No kind checked is a real, if useless, in-between
    state - same as a freshly-added row before a model has been typed;
    never auto-checked with a guessed kind, same "we consequently
    assign, never suggest" stance the no-default-address fix for a
    freshly-placed DI/DO block already takes."""

    changed = Signal()
    _MAX_CHANNELS = 999

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(6)
        self._checks = {}
        self._spins = {}
        for kind in CHANNEL_KINDS:
            check = QCheckBox(kind)
            check.setToolTip(tr("cards.kind_tooltip", kind=kind))
            spin = QSpinBox()
            spin.setRange(1, self._MAX_CHANNELS)
            spin.setValue(1)
            # User report (real screenshot): "liczba nie wiadomo jest do
            # czego" - a greyed "1" next to every UNCHECKED kind read as
            # four unexplained numbers in a row. An unchecked kind now
            # shows no number at all (hidden, not just disabled), and the
            # number a checked kind does show carries its own unit, so
            # "DI 16 ch." can only mean one thing.
            spin.setSuffix(tr("cards.channels_suffix"))
            spin.setFixedWidth(64)
            spin.setVisible(False)
            check.toggled.connect(lambda checked, k=kind: self._on_toggled(k, checked))
            spin.valueChanged.connect(lambda _v: self.changed.emit())
            layout.addWidget(check)
            layout.addWidget(spin)
            self._checks[kind] = check
            self._spins[kind] = spin
        layout.addStretch(1)

    def _on_toggled(self, kind, checked):
        self._spins[kind].setVisible(checked)
        self.changed.emit()

    def channel_kinds(self) -> dict:
        return {kind: self._spins[kind].value() for kind in CHANNEL_KINDS if self._checks[kind].isChecked()}

    def set_channel_kinds(self, channel_kinds: dict):
        """Populates from `channel_kinds` without emitting `changed` -
        each checkbox/spinbox is blocked individually (QWidget.
        blockSignals() does not propagate to children)."""
        for kind in CHANNEL_KINDS:
            check, spin = self._checks[kind], self._spins[kind]
            count = channel_kinds.get(kind)
            has_it = count is not None
            check.blockSignals(True)
            spin.blockSignals(True)
            check.setChecked(has_it)
            spin.setVisible(has_it)
            if has_it:
                spin.setValue(max(1, count))
            check.blockSignals(False)
            spin.blockSignals(False)


class CardsPanel(QWidget):
    """"Skład urządzenia" - the physical ELA/ADA/EPM I/O module registry:
    address (id), model, channel kinds (DI/DO/AI/AO, each with its own
    channel count - _ChannelKindsEditor above) - SPEC's own "Sprzęt"
    section, plus each module's own Modbus unit address (task: "ELA i
    ADA i EPM będą łączyły się z orange pi [...] po modbus - trzeba dać
    opcję adresowania") and the one shared bus (port/baud, or a TCP
    gateway) every module sits on - see project_format.ModbusBusConfig's
    own docstring for why this is GREENFIELD, not copied from an
    existing runtime driver. Locations moved out to their own
    LocationsPanel/tree branch (task "ostatnie dwa działy"). Editing a
    card's channel kinds re-runs sync_points_for_card() - "karty rodzą
    punkty" happens HERE, not in the point registry panel, which only
    ever shows what cards already produced."""

    _CARD_COLS = ["id", "model", "channel_kinds", "modbus_unit_id", "location", "responds"]
    _RESPONDS_COL = 5

    def __init__(self, studio_window, parent=None):
        super().__init__(parent)
        self._studio_window = studio_window
        self._loading = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.cards_table = QTableWidget(0, len(self._CARD_COLS))
        self.cards_table.setHorizontalHeaderLabels([
            tr("cards.col_id"), tr("cards.col_model"), tr("cards.col_channel_kinds"),
            tr("cards.col_modbus_unit_id"), tr("cards.col_location"),
        ])
        _prep_table(self.cards_table)
        _make_column_resizable(self.cards_table, 1, 220)
        # Four "kind + count" pairs side by side (_ChannelKindsEditor) -
        # wide enough for all four with their counts shown, still
        # draggable like every other column.
        _make_column_resizable(self.cards_table, 2, 470)
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
        location_codes = [l.code for l in project.locations]
        self.cards_table.setRowCount(0)
        for card in project.cards:
            self._append_card_row(card, location_codes)

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

    def _append_card_row(self, card: Card, location_codes=()):
        row = self.cards_table.rowCount()
        self.cards_table.insertRow(row)
        self.cards_table.setItem(row, 0, QTableWidgetItem(card.id))
        self.cards_table.setItem(row, 1, QTableWidgetItem(card.model))
        kinds_editor = _ChannelKindsEditor()
        kinds_editor.set_channel_kinds(card.channel_kinds)
        kinds_editor.changed.connect(lambda r=row: self._on_channel_kinds_changed(r))
        self.cards_table.setCellWidget(row, 2, kinds_editor)
        modbus_item = QTableWidgetItem(_fmt(card.modbus_unit_id))
        self._style_modbus_item(modbus_item, card.modbus_unit_id)
        self.cards_table.setItem(row, 3, modbus_item)

        # User report 3.4: where the MODULE itself physically sits - the
        # default every one of its own points inherits (project_panels.py's
        # own effective_location()), never a claim about where every
        # terminal on it actually goes.
        card_loc_combo = QComboBox()
        card_loc_combo.addItem(tr("cards.location_blank"), "")
        for code in location_codes:
            card_loc_combo.addItem(code, code)
        idx = card_loc_combo.findData(card.location)
        card_loc_combo.setCurrentIndex(idx if idx >= 0 else 0)
        card_loc_combo.currentIndexChanged.connect(lambda _i, r=row: self._on_card_location_changed(r))
        responds = QTableWidgetItem("")
        responds.setFlags(responds.flags() & ~Qt.ItemFlag.ItemIsEditable)
        responds.setBackground(_GREY_READONLY_BG)
        self.cards_table.setItem(row, self._RESPONDS_COL, responds)
        self._paint_responds_cell(row, card.id)
        self.cards_table.setCellWidget(row, 4, card_loc_combo)

    # -- live: SafetyKernel's Safety.<card>.Healthy says whether the module answers ----------------

    def _paint_responds_cell(self, row: int, card_id: str):
        item = self.cards_table.item(row, self._RESPONDS_COL)
        if item is None:
            return
        entry = getattr(self, "_live_tags", {}).get(f"Safety.{card_id}.Healthy")
        if entry is None:
            item.setText("")
            item.setBackground(_GREY_READONLY_BG)
            return
        healthy = bool(entry.get("value"))
        item.setText(tr("cards.responds_yes") if healthy else tr("cards.responds_no"))
        item.setBackground(_LIVE_BG if healthy else _LIVE_BAD_BG)

    def apply_live(self, tags: dict, forces: dict = None):
        self._live_tags = dict(tags or {})
        for row in range(self.cards_table.rowCount()):
            self._paint_responds_cell(row, self.cards_table.item(row, 0).text())

    def responds_rows(self) -> list:
        return [(self.cards_table.item(r, 0).text(), self.cards_table.item(r, self._RESPONDS_COL).text())
                for r in range(self.cards_table.rowCount())]

    def _on_card_location_changed(self, row):
        if self._loading:
            return
        project = self._studio_window._project
        card = project.cards[row]
        combo = self.cards_table.cellWidget(row, 4)
        card.location = combo.currentData() or ""
        project.touch()
        self._studio_window._on_project_changed()
        # Task 3.4's own requirement: this must NEVER touch project.points
        # - every point that inherits (location is None) picks up the new
        # value automatically the next time it's READ (effective_location()),
        # and every point with its own explicit override stays exactly as
        # the user left it. Nothing to refresh here for that reason; the
        # point registry panel re-resolves on its own next open/refresh.

    def _style_modbus_item(self, item: QTableWidgetItem, unit_id):
        if unit_id is None:
            item.setBackground(_MISSING_MODBUS_BG)
            item.setToolTip(tr("cards.modbus_unit_missing_tooltip"))
        else:
            item.setBackground(QBrush())
            item.setToolTip("")

    # -- row add/remove (called by menus.py's build_cards_toolbar) -----

    def add_card(self):
        project = self._studio_window._project
        existing_ids = {c.id for c in project.cards}
        new_id = _next_unique(existing_ids, "KARTA")
        # No kind checked yet - "we consequently assign, never suggest",
        # same stance the no-default-address fix for a freshly-placed
        # DI/DO block already takes; the user picks what this card has
        # in _ChannelKindsEditor rather than starting from a guess.
        card = Card(id=new_id, model="", channel_kinds={})
        # User report #2: the id stays "KARTA<n>" until a model is
        # typed - see _on_card_item_changed()'s own model-column branch,
        # which re-suggests it from the model while this flag is set,
        # and clears it the moment the user edits the id directly.
        card._id_is_auto = True
        # User report #3: never leave a new card silently unaddressed.
        card.modbus_unit_id = _next_free_modbus_unit_id(project)
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
        old_id = card.id

        if item.column() == 0:
            # Editing the id directly takes it out of "auto" mode - it
            # stays a user-editable field, we just stop overwriting it
            # once they've typed their own (user report #2).
            card._id_is_auto = False

        new_model = self.cards_table.item(row, 1).text()
        if item.column() == 1 and getattr(card, "_id_is_auto", False):
            suggested_id = _next_unique(
                {c.id for c in project.cards if c is not card}, _id_prefix_for_model(new_model),
            )
            self._loading = True
            self.cards_table.item(row, 0).setText(suggested_id)
            self._loading = False

        new_id = self.cards_table.item(row, 0).text().strip()
        # User report 3.2: id is the FIRST segment of the address grammar
        # ("<id>.<KIND>.<channel>") - a dot or space in it would silently
        # break parsing (a dot splits the grammar into the wrong number
        # of segments; shared/addressing.py's own parse_address() treats
        # surrounding whitespace as part of the card name, not an error).
        # Checked here, not in shared/addressing.py itself (GRANICE: this
        # task doesn't touch the grammar) - a UI-level input rule, same
        # spirit as _LOCATION_CODE_RE below.
        if new_id and new_id != card.id and ("." in new_id or " " in new_id):
            QMessageBox.warning(self, tr("cards.invalid_id_title"), tr("cards.invalid_id_text", id=new_id))
            self._loading = True
            self.cards_table.item(row, 0).setText(card.id)
            self._loading = False
            new_id = card.id
        elif new_id and new_id != card.id and any(c.id == new_id for c in project.cards if c is not card):
            # id is unique again, plain and simple - a card can now have
            # several channel kinds ITSELF (task follow-up, user report:
            # "karta ELA1 ma DI oraz AI"; see Card's own docstring for
            # why an earlier version of this fix, two rows sharing an
            # id, was abandoned), so there is no longer a "same id,
            # different kind" case to make room for here.
            QMessageBox.warning(self, tr("cards.duplicate_id_title"), tr("cards.duplicate_id_text", id=new_id))
            self._loading = True
            self.cards_table.item(row, 0).setText(card.id)
            self._loading = False
            new_id = card.id
        card.id = new_id or card.id
        card.model = new_model

        # User report #3: range AND uniqueness both validated, each with
        # its own message - a duplicate address is a different mistake
        # from a non-numeric/out-of-range one, and conflating them into
        # one generic warning would leave the user guessing which it was.
        modbus_text = self.cards_table.item(row, 3).text().strip()
        if not modbus_text:
            card.modbus_unit_id = None
        elif not modbus_text.isdigit() or not (1 <= int(modbus_text) <= 247):
            QMessageBox.warning(
                self, tr("cards.invalid_modbus_unit_title"), tr("cards.invalid_modbus_unit_text")
            )
            self._loading = True
            self.cards_table.item(row, 3).setText(_fmt(card.modbus_unit_id))
            self._loading = False
        else:
            unit_id = int(modbus_text)
            if unit_id != card.modbus_unit_id and any(c.modbus_unit_id == unit_id for c in project.cards if c is not card):
                QMessageBox.warning(
                    self, tr("cards.duplicate_modbus_unit_title"),
                    tr("cards.duplicate_modbus_unit_text", unit_id=unit_id),
                )
                self._loading = True
                self.cards_table.item(row, 3).setText(_fmt(card.modbus_unit_id))
                self._loading = False
            else:
                card.modbus_unit_id = unit_id
        self._style_modbus_item(self.cards_table.item(row, 3), card.modbus_unit_id)

        if old_id != card.id:
            # id changed - the OLD points are orphaned (their address no
            # longer matches anything this card would generate); drop
            # them under the old identity, then regenerate under the
            # new one, same as a fresh card.
            old_prefixes = tuple(f"{old_id}.{kind}." for kind in card.channel_kinds)
            project.points = [p for p in project.points if not p.address.startswith(old_prefixes)]
        sync_points_for_card(project, card)
        project.touch()
        self._studio_window._on_project_changed()

    def _on_channel_kinds_changed(self, row):
        project = self._studio_window._project
        card = project.cards[row]
        editor = self.cards_table.cellWidget(row, 2)
        new_kinds = editor.channel_kinds()
        if new_kinds == card.channel_kinds:
            return
        # A kind's count SHRINKING is handled by sync_points_for_card()
        # itself (that kind's prefix is still in card.channel_kinds, so
        # its own cleanup pass still sees it) - but a kind REMOVED
        # entirely (unchecked) drops its prefix from channel_kinds along
        # with it, and sync_points_for_card() can only clean up prefixes
        # it still knows about. Those points would otherwise be orphaned
        # forever - removed explicitly here first, same as an id CHANGE
        # already has to (_on_card_item_changed above).
        removed_kinds = set(card.channel_kinds) - set(new_kinds)
        if removed_kinds:
            removed_prefixes = tuple(f"{card.id}.{kind}." for kind in removed_kinds)
            project.points = [p for p in project.points if not p.address.startswith(removed_prefixes)]
        card.channel_kinds = new_kinds
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
        "warning_threshold",   # DI only: the switching counter's warning threshold (a setting)
        "device",
        "live",                # the controller's value while "Na żywo" is on; red while forced
    ]
    _LIVE_COL = 13

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
        # User report 3.4 ("zaznaczenie wielu wierszy -> ustawienie
        # lokalizacji wszystkim naraz") - the default QAbstractItemView
        # selection mode only ever keeps ONE row, so a shift/ctrl-click
        # range would silently collapse to the last-clicked row alone.
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.resizeColumnsToContents()
        _make_column_resizable(self.table, 1, 260)
        self.table.setColumnWidth(0, 90)
        self.table.setColumnWidth(3, 160)
        # SPEC "Studio - sterownik": live values next to the points, and
        # the force table (Engineer, force mode on) from the row's menu.
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._point_context_menu)
        layout.addWidget(self.table)
        self._live_tags = {}
        self._live_forces = {}

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
            # A card can have more than one kind now (task follow-up,
            # user report: "karta ELA1 ma DI oraz AI") - every kind it
            # has, in CHANNEL_KINDS' own canonical order.
            kinds_label = ", ".join(k for k in CHANNEL_KINDS if k in card.channel_kinds)
            self.card_filter.addItem(f"{card.id} ({kinds_label})", card.id)
        idx = self.card_filter.findData(current_filter)
        self.card_filter.setCurrentIndex(idx if idx >= 0 else 0)
        self.card_filter.blockSignals(False)
        active_filter = self.card_filter.currentData()

        location_codes = [l.code for l in project.locations]
        card_by_id = {c.id: c for c in project.cards}
        owners = point_owner_map(project)

        # User feedback (real screenshot, KARTA2.DO.* filtered): 7 grey,
        # unusable analog columns dominating the screen when looking at
        # one DI/DO card is noise, not "wyszarzone nie usunięte" (that
        # rule is for a MIXED table, not a single-kind filtered view).
        # Filtered to one card whose kind is digital -> hide them
        # outright; filtered to an analog card, a card spanning both
        # digital and analog kinds, or "Wszystkie karty" (mixed kinds,
        # can't pick one answer), keep them visible.
        filtered_card = card_by_id.get(active_filter) if active_filter else None
        filtered_kinds = set(filtered_card.channel_kinds) if filtered_card is not None else None
        hide_analog_cols = bool(filtered_kinds) and not (filtered_kinds & _ANALOG_KINDS)
        for col in range(4, 11):
            self.table.setColumnHidden(col, hide_analog_cols)

        self.table.setRowCount(0)
        points = sorted(project.points, key=lambda p: _address_sort_key(p.address))
        for point in points:
            addr_card, addr_kind, _channel = parse_address(point.address)
            if active_filter and addr_card != active_filter:
                continue
            self._append_point_row(
                point, addr_kind, location_codes, owners.get(point.address),
                card_by_id.get(addr_card),
            )
        self._loading = False

    def _append_point_row(self, point: Point, card_kind: str, location_codes, owner_id, card=None):
        row = self.table.rowCount()
        self.table.insertRow(row)

        addr_item = QTableWidgetItem(point.address)
        addr_item.setFlags(addr_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        addr_item.setBackground(_GREY_READONLY_BG)
        addr_item.setToolTip(point.address)
        self.table.setItem(row, 0, addr_item)

        self.table.setItem(row, 1, QTableWidgetItem(point.description))

        # User report 3.4: "widok ma pokazywać, która wartość jest
        # dziedziczona, a która ustawiona ręcznie" - the inherit entry's
        # own label names what it currently resolves to (the card's
        # location, live - not frozen at row-build time), and the whole
        # combo is italicized while that entry is selected. A location
        # code the project no longer has (a stale explicit value) still
        # gets its own entry appended so it stays visible/selected
        # rather than silently snapping to something else.
        loc_combo = QComboBox()
        inherited_value = card.location if card is not None else ""
        loc_combo.addItem(
            tr("points.location_inherit", value=inherited_value or tr("points.location_blank")),
            _INHERIT_LOCATION_SENTINEL,
        )
        loc_combo.addItem(tr("points.location_blank"), "")
        codes = list(location_codes)
        if point.location and point.location not in codes:
            codes.append(point.location)
        for code in codes:
            loc_combo.addItem(code, code)
        if point.location is None:
            loc_combo.setCurrentIndex(0)
            font = loc_combo.font()
            font.setItalic(True)
            loc_combo.setFont(font)
        else:
            idx = loc_combo.findData(point.location)
            loc_combo.setCurrentIndex(idx if idx >= 0 else 1)
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

        threshold_item = QTableWidgetItem(_fmt(point.warning_threshold) if card_kind == "DI" else "")
        if card_kind != "DI":
            threshold_item.setFlags(threshold_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            threshold_item.setBackground(_GREY_READONLY_BG)
        self.table.setItem(row, 11, threshold_item)

        # "Aparat" - read-only, computed from every device's feedback/
        # command lists (point_owner_map()) - SPEC's own "Aparat zużywa
        # punkty": this is the first place that occupancy becomes
        # actually VISIBLE, not just enforced at assignment time.
        device_item = QTableWidgetItem(owner_id or "")
        device_item.setFlags(device_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        device_item.setBackground(_GREY_READONLY_BG)
        if owner_id:
            device_item.setToolTip(owner_id)
        self.table.setItem(row, 12, device_item)

        live_item = QTableWidgetItem("")
        live_item.setFlags(live_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        live_item.setBackground(_GREY_READONLY_BG)
        self.table.setItem(row, self._LIVE_COL, live_item)
        self._paint_live_cell(row, point.address)

    # -- live values and forces (controller_link.LiveMonitor -> apply_live) ---------------------

    @staticmethod
    def format_live(entry) -> str:
        value = entry.get("value")
        if isinstance(value, bool):
            text = "1" if value else "0"
        elif isinstance(value, float):
            text = f"{value:.3f}".rstrip("0").rstrip(".")
        else:
            text = "" if value is None else str(value)
        quality = entry.get("quality") or "GOOD"
        return text if quality == "GOOD" else f"{text} ({quality})"

    def _paint_live_cell(self, row: int, address: str):
        item = self.table.item(row, self._LIVE_COL)
        if item is None:
            return
        entry = self._live_tags.get(address)
        force = self._live_forces.get(address)
        if force is not None:
            item.setText(tr("points.live_forced", value=self.format_live({"value": force.get("value")})))
            item.setBackground(_FORCED_BG)
            item.setToolTip(tr("points.live_forced_tooltip", actor=force.get("actor") or "?"))
        elif entry is not None:
            item.setText(self.format_live(entry))
            item.setBackground(_LIVE_BAD_BG if (entry.get("quality") or "GOOD") != "GOOD" else _LIVE_BG)
            item.setToolTip("")
        else:
            item.setText("")
            item.setBackground(_GREY_READONLY_BG)
            item.setToolTip("")

    def apply_live(self, tags: dict, forces: dict):
        """The monitor's latest read ({} when live is off or the link is down)."""
        self._live_tags = dict(tags or {})
        self._live_forces = dict(forces or {})
        for row in range(self.table.rowCount()):
            self._paint_live_cell(row, self.table.item(row, 0).text())

    def live_rows(self) -> list:
        """[(address, live text, forced)] - what the live column shows (tests)."""
        return [(self.table.item(r, 0).text(), self.table.item(r, self._LIVE_COL).text(),
                 self.table.item(r, 0).text() in self._live_forces) for r in range(self.table.rowCount())]

    def _selected_addresses(self) -> list:
        rows = sorted({idx.row() for idx in self.table.selectionModel().selectedRows()})
        return [self.table.item(r, 0).text() for r in rows]

    def _point_context_menu(self, pos):
        row = self.table.rowAt(pos.y())
        if row < 0:
            return
        if not self.table.item(row, 0).isSelected():
            self.table.selectRow(row)
        menu = QMenu(self)
        force_mode = self._studio_window.force_mode_enabled()
        force_action = menu.addAction(tr("points.force_value"))
        force_action.setEnabled(force_mode)
        release_action = menu.addAction(tr("points.release_force"))
        release_action.setEnabled(force_mode and any(a in self._live_forces for a in self._selected_addresses()))
        chosen = menu.exec(self.table.viewport().mapToGlobal(pos))
        if chosen is force_action:
            self.force_selected_points()
        elif chosen is release_action:
            self.release_selected_forces()

    def force_selected_points(self):
        """One value for every selected point (a dialog: 0/1 for a digital
        point, a number for an analog one) -> POST /api/v1/forces each."""
        addresses = self._selected_addresses()
        if not addresses or not self._studio_window.force_mode_enabled():
            return
        kinds = {parse_address(a)[1] for a in addresses}
        digital = kinds <= {"DI", "DO"}
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("points.force_dialog_title"))
        form = QVBoxLayout(dialog)
        form.addWidget(QLabel(tr("points.force_dialog_text", points=", ".join(addresses))))
        if digital:
            editor = QComboBox()
            editor.addItem("1 (TRUE)", True)
            editor.addItem("0 (FALSE)", False)
        else:
            editor = QDoubleSpinBox()
            editor.setRange(-1_000_000.0, 1_000_000.0)
            editor.setDecimals(3)
        form.addWidget(editor)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addWidget(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        value = editor.currentData() if digital else float(editor.value())
        self.apply_forces([(address, value) for address in addresses])

    def apply_forces(self, requests: list) -> list:
        """[(address, value)] -> the controller; returns [(address, reason)] refused."""
        link = self._studio_window.controller_link()
        refused = []
        for address, value in requests:
            ok, result = link.request_json("/api/v1/forces", {"tag": address, "value": value})
            if not ok:
                detail = link.last_error_detail
                reason = detail.get("reason") if isinstance(detail, dict) else result
                refused.append((address, reason))
        if refused:
            QMessageBox.warning(self, tr("points.force_dialog_title"),
                                tr("points.force_refused", details="\n".join(f"{a}: {r}" for a, r in refused)))
        self._studio_window.live_monitor().poll()
        return refused

    def release_selected_forces(self):
        link = self._studio_window.controller_link()
        for address in self._selected_addresses():
            if address in self._live_forces:
                link.request(f"/api/v1/forces/{address}", method="DELETE", timeout=6.0)
        self._studio_window.live_monitor().poll()

    def set_location_for_selected(self):
        """User report 3.4: "zaznaczenie wielu wierszy -> ustawienie
        lokalizacji wszystkim naraz" - one small dialog (the same three-
        way choice each row's own combo offers: inherit from the card /
        explicitly blank / a real code), applied to every selected row's
        Point in one go. A no-op (not even an empty-selection warning -
        the toolbar button itself should simply do nothing) when nothing
        is selected."""
        rows = sorted({idx.row() for idx in self.table.selectionModel().selectedRows()})
        if not rows:
            return
        project = self._studio_window._project
        location_codes = [l.code for l in project.locations]

        dialog = QDialog(self)
        dialog.setWindowTitle(tr("points.set_location_dialog_title"))
        form = QVBoxLayout(dialog)
        combo = QComboBox()
        combo.addItem(tr("points.location_inherit", value=tr("points.location_blank")), _INHERIT_LOCATION_SENTINEL)
        combo.addItem(tr("points.location_blank"), "")
        for code in location_codes:
            combo.addItem(code, code)
        form.addWidget(combo)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addWidget(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        data = combo.currentData()
        new_location = None if data == _INHERIT_LOCATION_SENTINEL else data
        addresses = {self.table.item(row, 0).text() for row in rows}
        for point in project.points:
            if point.address in addresses:
                point.location = new_location
        project.touch()
        self._studio_window._on_project_changed()
        self.refresh()

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
        data = combo.currentData()
        # User report 3.4: the sentinel means "back to inheriting the
        # card's own location" - None, not "" (see Point.location's own
        # docstring for why the two are never interchangeable). Anything
        # else (including "") is the user's own explicit choice for THIS
        # point, even one that happens to equal the card's location - an
        # explicit re-statement is still explicit, not a reason to snap
        # back to inherited.
        point.location = None if data == _INHERIT_LOCATION_SENTINEL else data
        project.touch()
        self._studio_window._on_project_changed()
        # Deferred, not called inline: refresh() rebuilds the whole table
        # (setRowCount(0) + re-append), which would delete THIS combo
        # while its own currentIndexChanged handler is still on the
        # stack - same "never rebuild from inside a cell widget's own
        # signal" reasoning _on_card_kind_changed's sibling in CardsPanel
        # already follows (it doesn't self-refresh at all). Only needed
        # here (not there) because this row's styling/label genuinely
        # depends on the new value (italic vs. normal, the inherited-
        # value text) - a plain data change elsewhere doesn't.
        QTimer.singleShot(0, self.refresh)

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
        elif col == 11:
            point.warning_threshold = _parse_int(text)
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
        for point in sorted(project.points, key=lambda p: _address_sort_key(p.address)):
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

    _COLS = ["id", "behavior", "kind", "feedback", "command", "command_style", "pulse_ms"]

    def __init__(self, studio_window, parent=None):
        super().__init__(parent)
        self._studio_window = studio_window
        self._loading = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.table = QTableWidget(0, len(self._COLS))
        self.table.setHorizontalHeaderLabels([tr(f"devices.col_{c}") for c in self._COLS])
        _make_column_resizable(self.table, 5, 200)
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

        # Task "wyłącznik jednocewkowy bistabilny": HOW the command
        # outputs drive the apparatus - a style, and the pulse time the
        # pulsed styles need. Only a SWITCHED apparatus is commanded at
        # all, so the two are inert for every other behavior.
        style_combo = QComboBox()
        for style in COMMAND_STYLES:
            style_combo.addItem(tr(f"devices.style_{style.lower()}"), style)
        idx = style_combo.findData(device.command_style)
        style_combo.setCurrentIndex(idx if idx >= 0 else 0)
        style_combo.setToolTip(tr("devices.style_tooltip"))
        style_combo.currentIndexChanged.connect(lambda _i, r=row: self._on_command_style_changed(r))
        self.table.setCellWidget(row, 5, style_combo)

        pulse_spin = QSpinBox()
        pulse_spin.setRange(0, 60_000)
        pulse_spin.setSuffix(" ms")
        pulse_spin.setValue(int(device.pulse_ms or 0))
        pulse_spin.valueChanged.connect(lambda _v, r=row: self._on_pulse_ms_changed(r))
        self.table.setCellWidget(row, 6, pulse_spin)
        self._sync_command_widgets(row, device)

    def _sync_command_widgets(self, row, device: Device):
        is_switched = device.behavior == "SWITCHED"
        self.table.cellWidget(row, 5).setEnabled(is_switched)
        self.table.cellWidget(row, 6).setEnabled(is_switched and device.command_style in _PULSED_STYLES)

    def _on_command_style_changed(self, row):
        if self._loading:
            return
        project = self._studio_window._project
        device = project.devices[row]
        device.command_style = self.table.cellWidget(row, 5).currentData()
        self._sync_command_widgets(row, device)
        project.touch()
        self._studio_window._on_project_changed()

    def _on_pulse_ms_changed(self, row):
        if self._loading:
            return
        project = self._studio_window._project
        device = project.devices[row]
        device.pulse_ms = self.table.cellWidget(row, 6).value()
        project.touch()
        self._studio_window._on_project_changed()

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
        self._sync_command_widgets(row, device)
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
    # A point's own address already names its kind (the grammar's own
    # middle segment) - reading it straight from there, rather than
    # looking a card up by id first, is correct regardless of how many
    # kinds that card itself has (task follow-up, user report: "karta
    # ELA1 ma DI oraz AI" - see Card's own docstring).
    result = []
    for point in sorted(project.points, key=lambda p: _address_sort_key(p.address)):
        _card, point_kind, _channel = parse_address(point.address)
        if point_kind == kind:
            result.append(point)
    return result


def _grouped_export_points(project):
    """Task point 7 - "Grupowanie po karcie, potem po lokalizacji."
    Shared by both export_points_csv()/export_points_html() below so
    the two formats can never silently disagree on row order. Returns
    [(Card, [(location_label, [Point, ...]), ...]), ...] - only cards
    that actually have points appear at all (an empty card contributes
    nothing to a terminal documentation table); a point with no
    location assigned is its own group, always LAST within its card
    (real, named locations first, in the project's own Lokalizacje
    order - matching how a reader would expect a printed table to
    read, not raw alphabetical)."""
    location_order = {loc.code: i for i, loc in enumerate(project.locations)}

    def _card_id_of(address):
        card, _kind, _channel = parse_address(address)
        return card

    points_by_card = {}
    for point in project.points:
        points_by_card.setdefault(_card_id_of(point.address), []).append(point)

    groups = []
    for card in project.cards:
        card_points = points_by_card.get(card.id, [])
        if not card_points:
            continue
        by_location = {}
        for point in card_points:
            # Task "jedno źródło listy kart" 3.4: the RESOLVED location
            # (the card's own default, unless this point has its own) -
            # otherwise every card-default point would print as "no
            # location", the exact printed-terminal-list use case this
            # whole feature exists for.
            by_location.setdefault(effective_location(point, card), []).append(point)
        location_labels = sorted(
            by_location.keys(),
            key=lambda loc: (loc == "", location_order.get(loc, 999), loc),
        )
        location_groups = [
            (label, sorted(by_location[label], key=lambda p: _address_sort_key(p.address)))
            for label in location_labels
        ]
        groups.append((card, location_groups))
    return groups


def _analog_export_fields(point: Point):
    """The task's own "dla AI/AO zakresy i jednostka" column group -
    empty for every non-analog point, same "wyszarzone/puste, nie
    wymyślone" stance PointRegistryPanel's own analog columns already
    take for a DI/DO row. Reads the KIND straight from the point's own
    address rather than its owning card's, since one card can now have
    more than one kind (task follow-up, user report: "karta ELA1 ma DI
    oraz AI") - a card's kind alone would no longer say which of ITS
    points this particular one is."""
    _card, kind, _channel = parse_address(point.address)
    if kind not in _ANALOG_KINDS:
        return "", "", ""
    raw_range = f"{_fmt(point.raw_min)}…{_fmt(point.raw_max)}" if (point.raw_min is not None or point.raw_max is not None) else ""
    eng_range = f"{_fmt(point.eng_min)}…{_fmt(point.eng_max)}" if (point.eng_min is not None or point.eng_max is not None) else ""
    return raw_range, eng_range, (point.unit or "")


def export_points_csv(project) -> str:
    """Task point 7 - "CSV (do Excela)". Columns verbatim, in the
    task's own order: adres, opis, lokalizacja, notatka techniczna,
    aparat korzystający z punktu, [AI/AO] zakres surowy/inżynieryjny/
    jednostka. No separate "karta" column (not in the task's own list) -
    "grupowanie po karcie" is expressed as ROW ORDER instead (every
    address is already card-prefixed, so sorting by address in Excel
    reproduces the same grouping) - see this module's own docstring
    convention of using row order, not an invented column, wherever the
    task's column list doesn't itself ask for one."""
    import csv
    import io

    owners = point_owner_map(project)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        tr("export.col_address"), tr("export.col_description"), tr("export.col_location"),
        tr("export.col_technical_note"), tr("export.col_device"),
        tr("export.col_raw_range"), tr("export.col_eng_range"), tr("export.col_unit"),
    ])
    for card, location_groups in _grouped_export_points(project):
        for location, points in location_groups:
            location_label = location or tr("export.no_location")
            for point in points:
                raw_range, eng_range, unit = _analog_export_fields(point)
                writer.writerow([
                    point.address, point.description, location_label, point.technical_note,
                    owners.get(point.address, ""), raw_range, eng_range, unit,
                ])
    return output.getvalue()


def export_points_html(project) -> str:
    """Task point 7 - "Markdown albo HTML (do wydruku)" - HTML chosen:
    directly printable from any browser (Ctrl+P), no separate renderer
    needed, unlike Markdown. A REAL grouped document (H2 per card, H3
    per location) - this is the "gotowa tabela zacisków do teczki
    powykonawczej" the task describes, not a dump of the same flat CSV
    rows with headers pasted on top."""
    import html as html_lib

    owners = point_owner_map(project)
    title = tr("export.document_title")
    parts = [
        "<!doctype html><html><head><meta charset=\"utf-8\">",
        f"<title>{html_lib.escape(title)}</title>",
        "<style>",
        "body{font-family:Arial,Helvetica,sans-serif;font-size:12px;color:#000;margin:24px;}",
        "h1{font-size:18px;margin-bottom:4px;}",
        ".subtitle{color:#555;margin-top:0;margin-bottom:24px;}",
        "h2{font-size:15px;margin-top:28px;border-bottom:2px solid #000;padding-bottom:2px;}",
        "h3{font-size:13px;margin-top:14px;color:#333;}",
        "table{border-collapse:collapse;width:100%;margin-bottom:10px;}",
        "th,td{border:1px solid #999;padding:4px 7px;text-align:left;vertical-align:top;}",
        "th{background:#e8e8e8;}",
        "@media print{h2{page-break-inside:avoid;}tr{page-break-inside:avoid;}}",
        "</style></head><body>",
        f"<h1>{html_lib.escape(title)}</h1>",
        f"<p class=\"subtitle\">{html_lib.escape(project.metadata.name)}"
        f" — {html_lib.escape(project.metadata.description)}</p>" if project.metadata.description
        else f"<p class=\"subtitle\">{html_lib.escape(project.metadata.name)}</p>",
    ]
    cols = [
        tr("export.col_location"), tr("export.col_address"), tr("export.col_description"),
        tr("export.col_technical_note"), tr("export.col_device"),
        tr("export.col_raw_range"), tr("export.col_eng_range"), tr("export.col_unit"),
    ]
    groups = _grouped_export_points(project)
    if not groups:
        parts.append(f"<p>{html_lib.escape(tr('export.no_points'))}</p>")
    for card, location_groups in groups:
        # A card can have more than one kind now (task follow-up, user
        # report: "karta ELA1 ma DI oraz AI") - every kind it has, in
        # CHANNEL_KINDS' own canonical order, not whatever order the
        # user happened to check the boxes in.
        kinds_label = ", ".join(k for k in CHANNEL_KINDS if k in card.channel_kinds)
        parts.append(f"<h2>{html_lib.escape(card.id)} — {html_lib.escape(card.model)} ({html_lib.escape(kinds_label)})</h2>")
        for location, points in location_groups:
            location_label = location or tr("export.no_location")
            parts.append(f"<h3>{html_lib.escape(location_label)}</h3>")
            parts.append("<table><tr>" + "".join(f"<th>{html_lib.escape(c)}</th>" for c in cols) + "</tr>")
            for point in points:
                raw_range, eng_range, unit = _analog_export_fields(point)
                row_cells = [
                    location_label, point.address, point.description, point.technical_note,
                    owners.get(point.address, ""), raw_range, eng_range, unit,
                ]
                parts.append("<tr>" + "".join(f"<td>{html_lib.escape(str(v))}</td>" for v in row_cells) + "</tr>")
            parts.append("</table>")
    parts.append("</body></html>")
    return "\n".join(parts)


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

        # The SOUNDER. Note what is not here: no output to pick. EPW-OS
        # publishes SSWIN.SIREN_ACTIVE / SIREN_TIME_LEFT / STROBE_ACTIVE
        # and the engineer wires those to a DO in Logic Studio (owner's
        # decision - "chce moc to swobodnie programowac ustawiajac bit
        # wewnetrzny alarm i pobudzenie danego DO ktory wyjdzie na
        # syrene"). What is configurable is only for how long it may
        # sound, and whether a hold-up line sounds at all.
        layout.addWidget(_section_label(tr("zones.sounder_heading")))
        sounder_hint = QLabel(tr("zones.sounder_hint"))
        sounder_hint.setWordWrap(True)
        layout.addWidget(sounder_hint)
        sounder_form = QFormLayout()
        self.siren_seconds_spin = QDoubleSpinBox()
        self.siren_seconds_spin.setRange(0.0, 3600.0)
        self.siren_seconds_spin.setDecimals(0)
        self.siren_seconds_spin.setSuffix(" s")
        self.siren_seconds_spin.setSpecialValueText(tr("zones.siren_no_limit"))
        self.panic_silent_check = QCheckBox(tr("zones.panic_silent"))
        sounder_form.addRow(tr("zones.siren_seconds"), self.siren_seconds_spin)
        sounder_form.addRow("", self.panic_silent_check)
        layout.addLayout(sounder_form)
        layout.addStretch(1)

        self.siren_seconds_spin.valueChanged.connect(self._on_sounder_changed)
        self.panic_silent_check.toggled.connect(self._on_sounder_changed)

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
        self.siren_seconds_spin.blockSignals(True)
        self.siren_seconds_spin.setValue(float(project.sounder.siren_seconds))
        self.siren_seconds_spin.blockSignals(False)
        self.panic_silent_check.blockSignals(True)
        self.panic_silent_check.setChecked(bool(project.sounder.panic_silent))
        self.panic_silent_check.blockSignals(False)
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

    def _on_sounder_changed(self):
        if self._loading:
            return
        project = self._studio_window._project
        project.sounder = Sounder(
            siren_seconds=float(self.siren_seconds_spin.value()),
            panic_silent=self.panic_silent_check.isChecked(),
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

        # Night (partial) arming - the one field that decides whether this
        # line still supervises while its zone is armed at night. Its own
        # group, not buried among the filters: it changes WHETHER the line
        # watches, not how it filters what it sees.
        night_box = QGroupBox(tr("lines.group_night"))
        night_layout = QVBoxLayout(night_box)
        self.night_check = QCheckBox(tr("intrusion.col_line_night"))
        night_layout.addWidget(self.night_check)
        night_hint = QLabel(tr("intrusion.line_night_hint"))
        night_hint.setWordWrap(True)
        night_layout.addWidget(night_hint)
        outer.addWidget(night_box)

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
        self.night_check.setChecked(bool(getattr(line, "active_at_night", True)))
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
        line.active_at_night = self.night_check.isChecked()
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


class IntrusionUsersPanel(QWidget):
    """Who may arm and disarm which zones ("stopnie dostępu" - the alarm
    system's own users, not the panel's three access LEVELS).

    A level answers "how much may whoever is standing at the keypad do".
    It cannot answer "only Kowalski may disarm the warehouse", because
    two operators are the same Operator to it. This panel is that answer:
    a person, the level their own code grants, and the zones they may
    operate - empty meaning every zone.

    NO CODE IS EDITED HERE, deliberately. A person's code is set on the
    controller itself (EPW-OS, Settings), so it never travels in
    projekt.epw - which goes to Studio, into git and over REST. What
    travels is who exists and what they may do.
    """

    _COLS = ["user_id", "user_name", "user_level", "user_zones", "user_enabled"]
    _LEVELS = ("User", "Operator", "Engineer")

    def __init__(self, studio_window, parent=None):
        super().__init__(parent)
        self._studio_window = studio_window
        self._loading = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        heading = QLabel(tr("intrusion.users_heading"))
        heading.setObjectName("PanelHeading")
        layout.addWidget(heading)
        intro = QLabel(tr("intrusion.users_intro"))
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self.table = QTableWidget(0, len(self._COLS))
        self.table.setHorizontalHeaderLabels([tr(f"intrusion.col_{c}") for c in self._COLS])
        _prep_table(self.table)
        _make_column_resizable(self.table, 1, 200)
        _make_column_resizable(self.table, 3, 260)
        self.table.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.table)

        self.refresh()

    # -- data ---------------------------------------------------------------

    def _project(self):
        return self._studio_window._project

    def refresh(self):
        self._loading = True
        try:
            project = self._project()
            users = list(project.intrusion_users)
            self.table.setRowCount(len(users))
            for row, user in enumerate(users):
                id_item = QTableWidgetItem(user.id)
                id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, 0, id_item)
                self.table.setItem(row, 1, QTableWidgetItem(user.name))

                level = QComboBox()
                level.addItems(self._LEVELS)
                level.setCurrentText(user.level if user.level in self._LEVELS else "Operator")
                level.currentTextChanged.connect(
                    lambda text, uid=user.id: self._set_level(uid, text))
                self.table.setCellWidget(row, 2, level)

                zones = QPushButton(self._zones_label(user))
                zones.clicked.connect(lambda checked=False, uid=user.id: self._edit_zones(uid))
                self.table.setCellWidget(row, 3, zones)

                enabled = QCheckBox()
                enabled.setChecked(bool(user.enabled))
                enabled.stateChanged.connect(
                    lambda state, uid=user.id: self._set_enabled(uid, bool(state)))
                self.table.setCellWidget(row, 4, enabled)
        finally:
            self._loading = False

    def _mark_changed(self):
        """Same two steps every other panel here takes after an edit:
        bump the project's own revision bookkeeping, then let the window
        re-render whatever depends on it."""
        self._project().touch()
        self._studio_window._on_project_changed()

    def _zones_label(self, user) -> str:
        if not user.zones:
            return tr("intrusion.user_zones_all")
        names = {z.id: z.name for z in self._project().zones}
        return ", ".join(names.get(zid, zid) for zid in user.zones)

    def _user(self, user_id):
        return next((u for u in self._project().intrusion_users if u.id == user_id), None)

    # -- editing ------------------------------------------------------------

    def add_user(self):
        project = self._project()
        existing = {u.id for u in project.intrusion_users}
        index = 1
        while f"U{index}" in existing:
            index += 1
        project.intrusion_users.append(IntrusionUser(id=f"U{index}", name=f"U{index}"))
        self._mark_changed()
        self.refresh()

    def remove_selected_user(self):
        row = self.table.currentRow()
        if row < 0 or row >= self.table.rowCount():
            return
        user_id = self.table.item(row, 0).text()
        project = self._project()
        project.intrusion_users = [u for u in project.intrusion_users if u.id != user_id]
        self._mark_changed()
        self.refresh()

    def _on_item_changed(self, item):
        if self._loading or item.column() != 1:
            return
        user = self._user(self.table.item(item.row(), 0).text())
        if user is not None:
            user.name = item.text().strip() or user.id
            self._mark_changed()

    def _set_level(self, user_id, level):
        if self._loading:
            return
        user = self._user(user_id)
        if user is not None and user.level != level:
            user.level = level
            self._mark_changed()

    def _set_enabled(self, user_id, enabled):
        if self._loading:
            return
        user = self._user(user_id)
        if user is not None and user.enabled != enabled:
            user.enabled = enabled
            self._mark_changed()

    def _edit_zones(self, user_id):
        user = self._user(user_id)
        if user is None:
            return
        dialog = _IntrusionUserZonesDialog(self._project(), user, self)
        if dialog.exec():
            user.zones = dialog.selected_zones()
            self._mark_changed()
            self.refresh()


class _IntrusionUserZonesDialog(QDialog):
    """Which zones one user may operate. Nothing ticked means every zone
    - the sensible default for a small site, and what a user created and
    never configured keeps."""

    def __init__(self, project, user, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("intrusion.col_user_zones"))
        layout = QVBoxLayout(self)
        hint = QLabel(tr("intrusion.user_zones_all"))
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self._checks = {}
        for zone in project.zones:
            check = QCheckBox(f"{zone.id} - {zone.name}")
            check.setChecked(zone.id in user.zones)
            layout.addWidget(check)
            self._checks[zone.id] = check
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selected_zones(self) -> list:
        return [zone_id for zone_id, check in self._checks.items() if check.isChecked()]


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


_MQTT_LINK_TYPES = ("BOOL", "REAL", "INT", "DINT", "STRING")


def _format_duration(seconds) -> str:
    """"3d 04:12:05" like runtime's switching_counters.format_duration -
    the same reading of the same number, so a value seen in Studio and
    on the panel look alike."""
    try:
        total = max(0, int(float(seconds)))
    except (TypeError, ValueError):
        total = 0
    days, rest = divmod(total, 86400)
    hours, rest = divmod(rest, 3600)
    minutes, secs = divmod(rest, 60)
    clock = f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{days}d {clock}" if days else clock


class MqttPanel(QWidget):
    """"Integracja MQTT" (KONFIGURACJA) - the project's MQTT settings
    (project_format.MqttConfig), decided 2026-09-18 to be a SETTING of
    the project rather than controller-local: the broker and topics
    belong to the installation, so they travel with the project and
    show up in the controller panel's live settings diff like a
    threshold does. The broker PASSWORD is deliberately not here - it
    stays in the controller's own local file (runtime's rule), typed on
    the panel once. Incoming mappings (`link_in`, remote topic -> local
    Link.* tag) and per-tag deadbands are the two tables."""

    _LINK_COLS = ("topic", "tag", "type", "stale_after_s")

    def __init__(self, studio_window, parent=None):
        super().__init__(parent)
        self._studio_window = studio_window
        self._loading = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        scroll.setWidget(content)
        outer.addWidget(scroll)

        intro = QLabel(tr("mqtt.intro"))
        intro.setWordWrap(True)
        layout.addWidget(intro)

        broker_box = QGroupBox(tr("mqtt.broker_heading"))
        form = QFormLayout(broker_box)
        self.enabled_check = QCheckBox(tr("mqtt.enabled"))
        form.addRow("", self.enabled_check)
        self.host_edit = QLineEdit()
        self.host_edit.setPlaceholderText("homeassistant.local")
        form.addRow(tr("mqtt.host"), self.host_edit)
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        form.addRow(tr("mqtt.port"), self.port_spin)
        self.username_edit = QLineEdit()
        form.addRow(tr("mqtt.username"), self.username_edit)
        self.tls_check = QCheckBox(tr("mqtt.tls"))
        form.addRow("", self.tls_check)
        self.client_id_edit = QLineEdit()
        form.addRow(tr("mqtt.client_id"), self.client_id_edit)
        self.prefix_edit = QLineEdit()
        self.prefix_edit.setPlaceholderText("epw/site1")
        form.addRow(tr("mqtt.topic_prefix"), self.prefix_edit)
        self.interval_spin = QDoubleSpinBox()
        self.interval_spin.setRange(0.1, 3600.0)
        self.interval_spin.setDecimals(1)
        self.interval_spin.setSuffix(" s")
        form.addRow(tr("mqtt.publish_interval"), self.interval_spin)
        self.deadband_spin = QDoubleSpinBox()
        self.deadband_spin.setRange(0.0, 1_000_000.0)
        self.deadband_spin.setDecimals(3)
        form.addRow(tr("mqtt.default_deadband"), self.deadband_spin)
        self.queue_spin = QSpinBox()
        self.queue_spin.setRange(1, 1_000_000)
        form.addRow(tr("mqtt.queue_max"), self.queue_spin)
        password_note = QLabel(tr("mqtt.password_note"))
        password_note.setWordWrap(True)
        password_note.setStyleSheet("color: #404040;")
        form.addRow("", password_note)
        layout.addWidget(broker_box)

        links_box = QGroupBox(tr("mqtt.links_heading"))
        links_layout = QVBoxLayout(links_box)
        links_hint = QLabel(tr("mqtt.links_hint"))
        links_hint.setWordWrap(True)
        links_layout.addWidget(links_hint)
        self.links_table = QTableWidget(0, len(self._LINK_COLS))
        self.links_table.setHorizontalHeaderLabels([tr(f"mqtt.col_{c}") for c in self._LINK_COLS])
        _prep_table(self.links_table)
        _make_column_resizable(self.links_table, 0, 260)
        self.links_table.itemChanged.connect(self._on_links_changed)
        links_layout.addWidget(self.links_table)
        links_buttons = QHBoxLayout()
        self.add_link_button = QPushButton(tr("mqtt.add_link"))
        self.add_link_button.clicked.connect(self.add_link)
        links_buttons.addWidget(self.add_link_button)
        self.remove_link_button = QPushButton(tr("mqtt.remove_link"))
        self.remove_link_button.clicked.connect(self.remove_selected_link)
        links_buttons.addWidget(self.remove_link_button)
        links_buttons.addStretch(1)
        links_layout.addLayout(links_buttons)
        layout.addWidget(links_box)

        deadband_box = QGroupBox(tr("mqtt.deadbands_heading"))
        deadband_layout = QVBoxLayout(deadband_box)
        self.deadband_table = QTableWidget(0, 2)
        self.deadband_table.setHorizontalHeaderLabels([tr("mqtt.col_tag"), tr("mqtt.col_deadband")])
        _prep_table(self.deadband_table)
        _make_column_resizable(self.deadband_table, 0, 260)
        self.deadband_table.itemChanged.connect(self._on_deadbands_changed)
        deadband_layout.addWidget(self.deadband_table)
        deadband_buttons = QHBoxLayout()
        self.add_deadband_button = QPushButton(tr("mqtt.add_deadband"))
        self.add_deadband_button.clicked.connect(self.add_deadband)
        deadband_buttons.addWidget(self.add_deadband_button)
        self.remove_deadband_button = QPushButton(tr("mqtt.remove_deadband"))
        self.remove_deadband_button.clicked.connect(self.remove_selected_deadband)
        deadband_buttons.addWidget(self.remove_deadband_button)
        deadband_buttons.addStretch(1)
        deadband_layout.addLayout(deadband_buttons)
        layout.addWidget(deadband_box)
        layout.addStretch(1)

        for widget, signal in (
            (self.enabled_check, self.enabled_check.toggled),
            (self.host_edit, self.host_edit.editingFinished),
            (self.port_spin, self.port_spin.valueChanged),
            (self.username_edit, self.username_edit.editingFinished),
            (self.tls_check, self.tls_check.toggled),
            (self.client_id_edit, self.client_id_edit.editingFinished),
            (self.prefix_edit, self.prefix_edit.editingFinished),
            (self.interval_spin, self.interval_spin.valueChanged),
            (self.deadband_spin, self.deadband_spin.valueChanged),
            (self.queue_spin, self.queue_spin.valueChanged),
        ):
            signal.connect(self._apply_form)
        self.refresh()

    def refresh(self):
        mqtt = self._studio_window._project.mqtt
        self._loading = True
        try:
            self.enabled_check.setChecked(bool(mqtt.enabled))
            self.host_edit.setText(mqtt.host)
            self.port_spin.setValue(int(mqtt.port))
            self.username_edit.setText(mqtt.username)
            self.tls_check.setChecked(bool(mqtt.tls))
            self.client_id_edit.setText(mqtt.client_id)
            self.prefix_edit.setText(mqtt.topic_prefix)
            self.interval_spin.setValue(float(mqtt.publish_interval_s))
            self.deadband_spin.setValue(float(mqtt.default_deadband))
            self.queue_spin.setValue(int(mqtt.queue_max))
            self.links_table.setRowCount(0)
            for entry in mqtt.link_in:
                self._append_link_row(entry)
            self.deadband_table.setRowCount(0)
            for tag, value in mqtt.deadband_per_tag.items():
                self._append_deadband_row(tag, value)
        finally:
            self._loading = False

    def _append_link_row(self, entry: dict):
        row = self.links_table.rowCount()
        self.links_table.insertRow(row)
        values = (str(entry.get("topic", "")), str(entry.get("tag", "")),
                  str(entry.get("type", "BOOL")), str(entry.get("stale_after_s", 30)))
        managed = bool(entry.get(OBJECT_LINK_MARK))
        for col, value in enumerate(values):
            item = QTableWidgetItem(value)
            if managed:
                # Written by the object's links panel (site_format.apply_object_links) - read here, edited there.
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                item.setBackground(_GREY_READONLY_BG)
                item.setToolTip(tr("mqtt.object_link_tooltip", source=entry.get("source", "?")))
            self.links_table.setItem(row, col, item)
        self.links_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, dict(entry))

    def _append_deadband_row(self, tag: str, value):
        row = self.deadband_table.rowCount()
        self.deadband_table.insertRow(row)
        self.deadband_table.setItem(row, 0, QTableWidgetItem(str(tag)))
        self.deadband_table.setItem(row, 1, QTableWidgetItem(str(value)))

    def _changed(self):
        self._studio_window._project.touch()
        self._studio_window._on_project_changed()

    def _apply_form(self, *_):
        if self._loading:
            return
        mqtt = self._studio_window._project.mqtt
        new = MqttConfig(
            enabled=self.enabled_check.isChecked(), host=self.host_edit.text().strip(),
            port=int(self.port_spin.value()), username=self.username_edit.text().strip(),
            tls=self.tls_check.isChecked(), client_id=self.client_id_edit.text().strip(),
            topic_prefix=self.prefix_edit.text().strip(), publish_interval_s=float(self.interval_spin.value()),
            default_deadband=float(self.deadband_spin.value()), deadband_per_tag=dict(mqtt.deadband_per_tag),
            queue_max=int(self.queue_spin.value()), link_in=list(mqtt.link_in),
        )
        if new != mqtt:
            self._studio_window._project.mqtt = new
            self._changed()

    # -- incoming mappings ---------------------------------------------------------------

    def _collect_links(self) -> list:
        links = []
        for row in range(self.links_table.rowCount()):
            cells = [self.links_table.item(row, col) for col in range(len(self._LINK_COLS))]
            topic, tag, type_name, stale = [(c.text().strip() if c is not None else "") for c in cells]
            type_name = type_name.upper() if type_name.upper() in _MQTT_LINK_TYPES else "BOOL"
            try:
                stale_after = int(float(stale))
            except ValueError:
                stale_after = 30
            original = cells[0].data(Qt.ItemDataRole.UserRole) if cells[0] is not None else None
            extra = dict(original) if isinstance(original, dict) else {}
            links.append({**extra, "topic": topic, "tag": tag, "type": type_name, "stale_after_s": stale_after})
        return links

    def _on_links_changed(self, _item=None):
        if self._loading:
            return
        links = self._collect_links()
        if links != self._studio_window._project.mqtt.link_in:
            self._studio_window._project.mqtt.link_in = links
            self._changed()

    def add_link(self):
        self._loading = True
        try:
            self._append_link_row({"topic": "", "tag": "Link.HA.In1", "type": "BOOL", "stale_after_s": 30})
        finally:
            self._loading = False
        self.links_table.setCurrentCell(self.links_table.rowCount() - 1, 0)
        self._on_links_changed()

    def remove_selected_link(self):
        row = self.links_table.currentRow()
        if row < 0:
            return
        original = self.links_table.item(row, 0).data(Qt.ItemDataRole.UserRole) if self.links_table.item(row, 0) else None
        if isinstance(original, dict) and original.get(OBJECT_LINK_MARK):
            QMessageBox.information(self, tr("mqtt.links_heading"), tr("mqtt.object_link_remove_there"))
            return
        self._loading = True
        try:
            self.links_table.removeRow(row)
        finally:
            self._loading = False
        self._on_links_changed()

    # -- per-tag deadbands ---------------------------------------------------------------

    def _collect_deadbands(self) -> dict:
        result = {}
        for row in range(self.deadband_table.rowCount()):
            tag_item, value_item = self.deadband_table.item(row, 0), self.deadband_table.item(row, 1)
            tag = tag_item.text().strip() if tag_item is not None else ""
            if not tag:
                continue
            try:
                result[tag] = float(value_item.text().strip()) if value_item is not None else 0.0
            except ValueError:
                result[tag] = 0.0
        return result

    def _on_deadbands_changed(self, _item=None):
        if self._loading:
            return
        deadbands = self._collect_deadbands()
        if deadbands != self._studio_window._project.mqtt.deadband_per_tag:
            self._studio_window._project.mqtt.deadband_per_tag = deadbands
            self._changed()

    def add_deadband(self):
        self._loading = True
        try:
            self._append_deadband_row("", 0.0)
        finally:
            self._loading = False
        self.deadband_table.setCurrentCell(self.deadband_table.rowCount() - 1, 0)

    def remove_selected_deadband(self):
        row = self.deadband_table.currentRow()
        if row < 0:
            return
        self._loading = True
        try:
            self.deadband_table.removeRow(row)
        finally:
            self._loading = False
        self._on_deadbands_changed()


class ObjectLinksPanel(QWidget):
    """"Powiązania obiektu" (KONFIGURACJA) - one controller's tag read by
    another controller of the same object, over MQTT (site_format.
    apply_object_links: the source publishes at <prefix>/tag/<path>/state,
    the target's mqtt.link_in turns it into a local Link.<Id>.In<n> tag
    its logic and screens use). The links belong to the OBJECT file;
    this panel writes them into the projects. Needs a real object with
    at least two controllers."""

    _COLS = ("source", "tag", "target", "link_tag", "type", "stale")

    def __init__(self, studio_window, parent=None):
        super().__init__(parent)
        self._studio_window = studio_window
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        intro = QLabel(tr("object_links.intro"))
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        self.table = QTableWidget(0, len(self._COLS))
        self.table.setHorizontalHeaderLabels([tr(f"object_links.col_{c}") for c in self._COLS])
        _prep_table(self.table)
        _make_column_resizable(self.table, 3, 240)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.table, 1)
        buttons = QHBoxLayout()
        self.add_button = QPushButton(tr("object_links.add"))
        self.add_button.clicked.connect(self.add_link)
        buttons.addWidget(self.add_button)
        self.remove_button = QPushButton(tr("object_links.remove"))
        self.remove_button.clicked.connect(self.remove_selected_link)
        buttons.addWidget(self.remove_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        self.refresh()

    def _devices(self) -> list:
        """[(rel path, name)] of the object's controllers, in tree order."""
        return self._studio_window.object_devices()

    def rows(self) -> list:
        site = self._studio_window._site
        names = dict(self._devices())
        return [(names.get(l["source"], l["source"]), l["tag"], names.get(l["target"], l["target"]), l["link_tag"],
                 l.get("type", "BOOL"), int(l.get("stale_after_s", 30))) for l in (site.links if site else [])]

    def refresh(self):
        site = self._studio_window._site
        devices = self._devices()
        ready = site is not None and self._studio_window._site_path and len(devices) >= 2
        self.add_button.setEnabled(bool(ready))
        self.table.setRowCount(0)
        for values in self.rows():
            row = self.table.rowCount()
            self.table.insertRow(row)
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(str(value)))
        self.remove_button.setEnabled(self.table.rowCount() > 0)
        if not ready:
            self.status_label.setText(tr("object_links.needs_object"))
        else:
            self.status_label.setText(tr("object_links.count", count=self.table.rowCount()))

    def add_link(self):
        devices = self._devices()
        if len(devices) < 2:
            return
        win = self._studio_window
        active_rel = win.active_device_rel()
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("object_links.add"))
        form = QFormLayout(dialog)
        source_combo = QComboBox()
        for rel, name in devices:
            source_combo.addItem(name, rel)
        # Default: the source is another controller than the active one.
        for i, (rel, _name) in enumerate(devices):
            if rel != active_rel:
                source_combo.setCurrentIndex(i)
                break
        form.addRow(tr("object_links.col_source"), source_combo)
        point_combo = QComboBox()
        form.addRow(tr("object_links.col_tag"), point_combo)
        target_combo = QComboBox()
        for rel, name in devices:
            target_combo.addItem(name, rel)
        idx = target_combo.findData(active_rel)
        target_combo.setCurrentIndex(idx if idx >= 0 else 0)
        form.addRow(tr("object_links.col_target"), target_combo)
        link_edit = QLineEdit()
        form.addRow(tr("object_links.col_link_tag"), link_edit)
        stale_spin = QSpinBox()
        stale_spin.setRange(1, 3600)
        stale_spin.setValue(30)
        stale_spin.setSuffix(" s")
        form.addRow(tr("object_links.col_stale"), stale_spin)

        def fill_points():
            point_combo.clear()
            project = win.project_for_rel(source_combo.currentData())
            for point in (project.points if project is not None else []):
                label = f"{point.address}  {point.description}".rstrip()
                point_combo.addItem(label, point.address)

        def suggest():
            source_name = source_combo.currentText()
            target = win.project_for_rel(target_combo.currentData())
            existing = [e.get("tag") for e in (target.mqtt.link_in if target is not None else [])]
            existing += [l["link_tag"] for l in win._site.links if l["target"] == target_combo.currentData()]
            link_edit.setText(suggest_link_tag(source_name, existing))
        source_combo.currentIndexChanged.connect(lambda _i: (fill_points(), suggest()))
        target_combo.currentIndexChanged.connect(lambda _i: suggest())
        fill_points()
        suggest()
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.create_link(source_combo.currentData(), point_combo.currentData(), target_combo.currentData(),
                         link_edit.text().strip(), int(stale_spin.value()))

    def create_link(self, source_rel: str, tag: str, target_rel: str, link_tag: str, stale_after_s: int = 30) -> bool:
        """Validates and adds one link, then writes the links into the projects."""
        win = self._studio_window
        if not tag or source_rel == target_rel:
            QMessageBox.warning(self, tr("object_links.add"), tr("object_links.invalid_same"))
            return False
        if not LINK_TAG_RE.match(link_tag or ""):
            QMessageBox.warning(self, tr("object_links.add"), tr("object_links.invalid_link_tag"))
            return False
        if any(l["target"] == target_rel and l["link_tag"] == link_tag for l in win._site.links):
            QMessageBox.warning(self, tr("object_links.add"), tr("object_links.duplicate_link_tag", tag=link_tag))
            return False
        win._site.links.append({"source": source_rel, "tag": tag, "target": target_rel, "link_tag": link_tag,
                                "type": link_type_for(tag), "stale_after_s": int(stale_after_s)})
        win._site.is_dirty = True
        changed = win.apply_object_links()
        self.refresh()
        if changed:
            self.status_label.setText(tr("object_links.applied", details="; ".join(
                f"{dict(self._devices()).get(rel, rel)}: {', '.join(what)}" for rel, what in changed.items())))
        return True

    def remove_selected_link(self):
        row = self.table.currentRow()
        win = self._studio_window
        if row < 0 or win._site is None or row >= len(win._site.links):
            return
        del win._site.links[row]
        win._site.is_dirty = True
        win.apply_object_links()
        self.refresh()


class ServiceNotesPanel(QWidget):
    """"Notatki serwisowe" (KONFIGURACJA) - the per-device logbook
    written at the cabinet (runtime's Service Notes, Operator+), read
    here. In the project since 2026-09-18: every note added on the panel
    comes back as revision +1 by "panel", so "Zgraj z urządzenia" or
    "Przyjmij nastawy ze sterownika" brings the installation's history
    into Studio. Read-only on purpose - runtime never edits or deletes a
    note either ("to dziennik, nie notatnik")."""

    _COLS = ("device", "description", "date", "author", "text")

    def __init__(self, studio_window, parent=None):
        super().__init__(parent)
        self._studio_window = studio_window
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        intro = QLabel(tr("service_notes.intro"))
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.count_label = QLabel()
        layout.addWidget(self.count_label)
        self.table = QTableWidget(0, len(self._COLS))
        self.table.setHorizontalHeaderLabels([tr(f"service_notes.col_{c}") for c in self._COLS])
        _prep_table(self.table)
        _make_column_resizable(self.table, 4, 420)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table, 1)
        self.refresh()

    def rows(self) -> list:
        """[(device tag, description, timestamp, author level, text)] oldest
        first within a device, devices in address order."""
        project = self._studio_window._project
        descriptions = {p.address: p.description for p in project.points}
        descriptions.update({d.id: d.name for d in project.devices if getattr(d, "name", "")})
        out = []
        for tag in sorted(project.service_notes):
            notes = project.service_notes.get(tag) or []
            for note in sorted(notes, key=lambda n: float(n.get("timestamp") or 0)):
                out.append((tag, descriptions.get(tag, ""), note.get("timestamp"), str(note.get("author_level", "")),
                            str(note.get("text", ""))))
        return out

    def refresh(self):
        from datetime import datetime
        rows = self.rows()
        self.table.setRowCount(0)
        for tag, description, timestamp, author, text in rows:
            row = self.table.rowCount()
            self.table.insertRow(row)
            try:
                when = datetime.fromtimestamp(float(timestamp)).strftime("%Y-%m-%d %H:%M:%S")
            except (TypeError, ValueError, OSError, OverflowError):
                when = "N/A"
            for col, value in enumerate((tag, description, when, author, text)):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, col, item)
        devices = len({r[0] for r in rows})
        self.count_label.setText(tr("service_notes.count", notes=len(rows), devices=devices))


class ProtectionTestsPanel(QWidget):
    """"Test zabezpieczeń" (STEROWNIK) - SPEC "Wymuszanie stanów -
    Powiązanie": the internal Omicron. The controller runs the test
    itself (runtime/epw_os/core/protection_test.py, REST
    /api/v1/protection-tests): a process protection has its analog
    point forced past the threshold and the trip is timed against the
    configured delay, then the reset; an apparatus is commanded and its
    feedback is timed, then restored. This panel only lists what the
    controller can test, starts one test (Engineer token), follows it
    and shows the reports the controller keeps - and writes them out as
    CSV for the commissioning file. Nothing here is project data."""

    _CAND_COLS = ("kind", "id", "name", "details", "state")
    _REPORT_COLS = ("started", "kind", "subject", "result", "configured", "measured", "reason")
    POLL_MS = 1000

    def __init__(self, studio_window, parent=None):
        super().__init__(parent)
        self._studio_window = studio_window
        self._reports = []
        self._candidates = []
        self._running_id = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        intro = QLabel(tr("protection_tests.intro"))
        intro.setWordWrap(True)
        layout.addWidget(intro)

        row = QHBoxLayout()
        self.refresh_button = QPushButton(tr("protection_tests.refresh"))
        self.refresh_button.clicked.connect(self.refresh)
        row.addWidget(self.refresh_button)
        self.run_button = QPushButton(tr("protection_tests.run"))
        self.run_button.clicked.connect(self.run_selected_test)
        row.addWidget(self.run_button)
        self.export_button = QPushButton(tr("protection_tests.export_csv"))
        self.export_button.clicked.connect(self.export_csv)
        row.addWidget(self.export_button)
        row.addStretch(1)
        layout.addLayout(row)

        self.status_label = QLabel(tr("protection_tests.status_idle"))
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        layout.addWidget(_section_label(tr("protection_tests.candidates_heading")))
        self.candidates_table = QTableWidget(0, len(self._CAND_COLS))
        self.candidates_table.setHorizontalHeaderLabels([tr(f"protection_tests.col_{c}") for c in self._CAND_COLS])
        _prep_table(self.candidates_table)
        self.candidates_table.doubleClicked.connect(lambda _index: self.run_selected_test())
        layout.addWidget(self.candidates_table, 1)

        layout.addWidget(_section_label(tr("protection_tests.reports_heading")))
        self.reports_table = QTableWidget(0, len(self._REPORT_COLS))
        self.reports_table.setHorizontalHeaderLabels([tr(f"protection_tests.rep_col_{c}") for c in self._REPORT_COLS])
        _prep_table(self.reports_table)
        self.reports_table.doubleClicked.connect(self._show_steps)
        layout.addWidget(self.reports_table, 2)

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(self.POLL_MS)
        self._poll_timer.timeout.connect(self._poll)

    # -- data -------------------------------------------------------------------------------

    def _link(self):
        return self._studio_window._controller_link

    def clear(self):
        """After a project swap: the other controller's lists mean nothing here."""
        self._poll_timer.stop()
        self._running_id = None
        self._reports, self._candidates = [], []
        self._fill_candidates()
        self._fill_reports()
        self.status_label.setText(tr("protection_tests.status_idle"))

    def refresh(self):
        ok, data = self._link().request("/api/v1/protection-tests", timeout=3.0)
        if not ok:
            self.clear()
            self.status_label.setText(tr("protection_tests.fetch_failed", reason=data))
            return False
        if not data.get("available", False):
            self.clear()
            self.status_label.setText(tr("protection_tests.unavailable"))
            return False
        candidates = data.get("candidates") or {}
        self._candidates = ([dict(c, kind="process") for c in candidates.get("process", [])]
                            + [dict(c, kind="apparatus") for c in candidates.get("apparatus", [])])
        self._reports = list(data.get("reports") or [])
        running = data.get("running")
        self._fill_candidates()
        self._fill_reports()
        if running:
            self._running_id = running["id"]
            self.status_label.setText(tr("protection_tests.status_running", subject=running["subject"]))
            self._poll_timer.start()
        else:
            self._poll_timer.stop()
            self._running_id = None
            self.status_label.setText(tr("protection_tests.status_ready", count=len(self._candidates),
                                         reports=len(self._reports)))
        self.run_button.setEnabled(running is None)
        return True

    def _fill_candidates(self):
        table = self.candidates_table
        table.setRowCount(0)
        for candidate in self._candidates:
            row = table.rowCount()
            table.insertRow(row)
            if candidate["kind"] == "process":
                details = tr("protection_tests.details_process", tag=candidate.get("analog_tag", ""),
                             upper=_fmt(candidate.get("upper_threshold")), lower=_fmt(candidate.get("lower_threshold")),
                             delay=_fmt(candidate.get("delay_seconds")))
                if candidate.get("exceeded"):
                    state = tr("protection_tests.state_exceeded")
                elif not candidate.get("enabled", True):
                    state = tr("protection_tests.state_disabled")
                else:
                    state = tr("protection_tests.state_ready")
            else:
                details = tr("protection_tests.details_apparatus", feedback=", ".join(candidate.get("feedback", [])),
                             command=", ".join(candidate.get("command", [])), style=candidate.get("command_style", ""))
                state = tr("protection_tests.state_ready")
            values = (tr(f"protection_tests.kind_{candidate['kind']}"), candidate["id"],
                      candidate.get("name") or candidate.get("kind_label") or candidate.get("kind", ""), details, state)
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                table.setItem(row, col, item)
        table.resizeColumnsToContents()

    def _fill_reports(self):
        table = self.reports_table
        table.setRowCount(0)
        for report in reversed(self._reports):
            row = table.rowCount()
            table.insertRow(row)
            values = (report.get("started_at", ""), tr(f"protection_tests.kind_{report.get('kind', 'process')}"),
                      report.get("subject", ""), report.get("result", ""), _summary(report.get("configured")),
                      _summary(report.get("measured")), report.get("reason", ""))
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if col == 3:
                    color = {"PASS": QColor("#1a7f1a"), "FAIL": QColor("#c00000"),
                             "BLOCKED": QColor("#a05a00")}.get(value)
                    if color is not None:
                        item.setForeground(color)
                table.setItem(row, col, item)
        table.resizeColumnsToContents()

    # -- actions ----------------------------------------------------------------------------

    def selected_candidate(self):
        row = self.candidates_table.currentRow()
        if row < 0 or row >= len(self._candidates):
            return None
        return self._candidates[row]

    def run_selected_test(self):
        candidate = self.selected_candidate()
        if candidate is None:
            self.status_label.setText(tr("protection_tests.select_row"))
            return False
        ok, data = self._link().request_json("/api/v1/protection-tests", {"kind": candidate["kind"], "id": candidate["id"]})
        if not ok:
            detail = self._link().last_error_detail
            reason = detail.get("reason") if isinstance(detail, dict) and detail.get("reason") else data
            if isinstance(detail, dict) and detail.get("report"):
                self._reports.append(detail["report"])
                self._fill_reports()
            self.status_label.setText(tr("protection_tests.start_failed", subject=candidate["id"], reason=reason))
            return False
        self._running_id = data.get("id")
        self.status_label.setText(tr("protection_tests.status_running", subject=data.get("subject", candidate["id"])))
        self.run_button.setEnabled(False)
        self._poll_timer.start()
        return True

    def _poll(self):
        if not self._running_id:
            self._poll_timer.stop()
            return
        ok, data = self._link().request(f"/api/v1/protection-tests/{self._running_id}", timeout=3.0)
        if not ok:
            self._poll_timer.stop()
            self.status_label.setText(tr("protection_tests.fetch_failed", reason=data))
            self.run_button.setEnabled(True)
            return
        if data.get("result") == "RUNNING":
            return
        self._poll_timer.stop()
        finished = data
        self._running_id = None
        self.refresh()
        self.status_label.setText(tr("protection_tests.finished", subject=finished.get("subject", ""),
                                     result=finished.get("result", ""), reason=finished.get("reason", "")))

    def _show_steps(self, index):
        row = index.row()
        reports = list(reversed(self._reports))
        if row < 0 or row >= len(reports):
            return
        report = reports[row]
        box = QMessageBox(self)
        box.setWindowTitle(tr("protection_tests.steps_title", subject=report.get("subject", "")))
        box.setText(f"{report.get('result', '')}: {report.get('reason', '')}")
        box.setDetailedText("\n".join(report.get("steps") or []))
        box.exec()

    def reports_csv(self) -> str:
        """One row per report - the commissioning file's own evidence."""
        out = io.StringIO()
        writer = csv.writer(out, delimiter=";", lineterminator="\n")
        writer.writerow(["started_at", "finished_at", "kind", "subject", "name", "actor", "result", "reason",
                         "configured", "measured", "steps"])
        for report in self._reports:
            writer.writerow([report.get("started_at", ""), report.get("finished_at", ""), report.get("kind", ""),
                             report.get("subject", ""), report.get("name", ""), report.get("actor", ""),
                             report.get("result", ""), report.get("reason", ""), _summary(report.get("configured")),
                             _summary(report.get("measured")), " | ".join(report.get("steps") or [])])
        return out.getvalue()

    def export_csv(self, path: str = None) -> bool:
        if not self._reports:
            self.status_label.setText(tr("protection_tests.no_reports"))
            return False
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, tr("protection_tests.export_csv"), "protection_tests.csv",
                                                  "CSV (*.csv)")
            if not path:
                return False
        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                f.write(self.reports_csv())
        except OSError as e:
            self.status_label.setText(tr("protection_tests.export_failed", reason=str(e)))
            return False
        self.status_label.setText(tr("protection_tests.csv_saved", path=path))
        return True


def _summary(values) -> str:
    if not isinstance(values, dict):
        return ""
    return ", ".join(f"{k}={_fmt(v)}" for k, v in values.items())


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

    "Wyślij do urządzenia" / "Zgraj z urządzenia" (task "wysyłanie
    projektu na sterownik przez REST", PROJEKT_EPW_ZADANIA p. 5) work
    against runtime's own project endpoints: GET /api/v1/project (the
    header with `revision` and `settings_hash`), GET /api/v1/project/
    settings (the controller's settings, for the diff), GET /api/v1/
    project/file (download, Engineer token) and POST /api/v1/project/
    install?expected_revision=N (upload, Engineer token; the controller
    refuses with 409 when its revision moved in between, and restarts
    itself on the new project). SPEC "Wersjonowanie" is applied here:
    before sending, the controller's settings_hash is compared with the
    saved project's; when they differ, the operator sees every setting
    that differs ("tu 25 A, tam 40 A") and decides - overwrite, or stop."""

    _SETTINGS_HOST = "controller/host"
    _SETTINGS_TOKEN = "controller/token"

    def __init__(self, studio_window, parent=None):
        super().__init__(parent)
        self._studio_window = studio_window

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        scroll.setWidget(content)
        outer.addWidget(scroll)

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

        # What the controller is actually EXECUTING, not just whether it
        # answers: /api/v1/health only ever says RUNNING/FAULT/DEGRADED
        # for the whole subsystem, which cannot tell "this project has no
        # logic" from "the program was refused". Filled by
        # _test_connection() below, from /api/v1/logic.
        self.logic_label = QLabel(tr("controller.logic_unknown"))
        self.logic_label.setWordWrap(True)
        layout.addWidget(self.logic_label)

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

        # SPEC "Studio — sterownik", point 4: the controller's settings,
        # live, next to the project's own, differences marked - and a way
        # to take the controller's values into the project without
        # pulling the whole file (GET /api/v1/project/settings +
        # project_format.settings_snapshot()/apply_settings_snapshot()).
        settings_box = QGroupBox(tr("controller.settings_heading"))
        settings_layout = QVBoxLayout(settings_box)
        settings_row = QHBoxLayout()
        self.settings_button = QPushButton(tr("controller.fetch_settings"))
        self.settings_button.clicked.connect(self._fetch_settings)
        settings_row.addWidget(self.settings_button)
        self.settings_live_check = QCheckBox(tr("controller.settings_live"))
        self.settings_live_check.toggled.connect(self._toggle_live_settings)
        settings_row.addWidget(self.settings_live_check)
        self.settings_diff_only_check = QCheckBox(tr("controller.settings_diff_only"))
        self.settings_diff_only_check.setChecked(True)
        self.settings_diff_only_check.toggled.connect(lambda _checked: self._render_settings())
        settings_row.addWidget(self.settings_diff_only_check)
        settings_row.addStretch(1)
        self.take_settings_button = QPushButton(tr("controller.take_settings"))
        self.take_settings_button.clicked.connect(self._take_controller_settings)
        self.take_settings_button.setEnabled(False)
        settings_row.addWidget(self.take_settings_button)
        settings_layout.addLayout(settings_row)
        self.settings_status_label = QLabel(tr("controller.settings_status_none"))
        self.settings_status_label.setWordWrap(True)
        settings_layout.addWidget(self.settings_status_label)
        self.settings_table = QTableWidget(0, 3)
        self.settings_table.setHorizontalHeaderLabels(
            [tr("controller.diff_col_setting"), tr("controller.diff_col_studio"), tr("controller.diff_col_controller")]
        )
        _prep_table(self.settings_table)
        _make_column_resizable(self.settings_table, 0, 360)
        settings_layout.addWidget(self.settings_table, 1)
        layout.addWidget(settings_box, 1)
        self._remote_settings = None          # the last GET /api/v1/project/settings body
        self._settings_timer = QTimer(self)
        self._settings_timer.setInterval(5000)
        self._settings_timer.timeout.connect(self._fetch_settings)

        # What stays on the controller and is NOT in the project (its
        # controller.local.json: language, REST, retentions...) - read-only
        # here, so nothing the controller holds is invisible from Studio
        # (decided 2026-09-18).
        local_box = QGroupBox(tr("controller.local_heading"))
        local_layout = QVBoxLayout(local_box)
        local_row = QHBoxLayout()
        self.local_button = QPushButton(tr("controller.fetch_local"))
        self.local_button.clicked.connect(self._fetch_local_settings)
        local_row.addWidget(self.local_button)
        self.local_status_label = QLabel(tr("controller.local_status_none"))
        self.local_status_label.setWordWrap(True)
        local_row.addWidget(self.local_status_label, 1)
        local_layout.addLayout(local_row)
        self.local_table = QTableWidget(0, 2)
        self.local_table.setHorizontalHeaderLabels([tr("controller.local_col_setting"), tr("controller.local_col_value")])
        _prep_table(self.local_table)
        _make_column_resizable(self.local_table, 0, 300)
        self.local_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        local_layout.addWidget(self.local_table)
        layout.addWidget(local_box, 1)
        self._local_settings = None

        # The switching counters as the panel shows them, zeroed from here
        # after a device was replaced (POST /api/v1/counters/<tag>/reset,
        # Engineer token) - the same reset the panel's own Engineer menu
        # does, audited the same way.
        counters_box = QGroupBox(tr("controller.counters_heading"))
        counters_layout = QVBoxLayout(counters_box)
        counters_row = QHBoxLayout()
        self.counters_button = QPushButton(tr("controller.fetch_counters"))
        self.counters_button.clicked.connect(self._fetch_counters)
        counters_row.addWidget(self.counters_button)
        self.reset_counter_button = QPushButton(tr("controller.reset_counter"))
        self.reset_counter_button.clicked.connect(self._reset_selected_counter)
        self.reset_counter_button.setEnabled(False)
        counters_row.addWidget(self.reset_counter_button)
        self.reset_all_counters_button = QPushButton(tr("controller.reset_all_counters"))
        self.reset_all_counters_button.clicked.connect(self._reset_all_counters)
        self.reset_all_counters_button.setEnabled(False)
        counters_row.addWidget(self.reset_all_counters_button)
        counters_row.addStretch(1)
        counters_layout.addLayout(counters_row)
        self.counters_status_label = QLabel(tr("controller.counters_status_none"))
        self.counters_status_label.setWordWrap(True)
        counters_layout.addWidget(self.counters_status_label)
        self.counters_table = QTableWidget(0, 5)
        self.counters_table.setHorizontalHeaderLabels([
            tr("controller.counters_col_tag"), tr("controller.counters_col_closes"),
            tr("controller.counters_col_opens"), tr("controller.counters_col_closed_time"),
            tr("controller.counters_col_threshold")])
        _prep_table(self.counters_table)
        _make_column_resizable(self.counters_table, 0, 220)
        self.counters_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.counters_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        counters_layout.addWidget(self.counters_table)
        layout.addWidget(counters_box, 1)
        self._remote_counters = None

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

    def _link(self):
        """studio/shell/controller_link.py - the one link every panel and
        the live monitor share; address and token per project file."""
        return self._studio_window.controller_link()

    def _load_connection_settings(self):
        link = self._link()
        self.host_edit.setText(link.host())
        self.token_edit.setText(link.token())

    def reload_connection(self):
        """After the active device changed (main_window._enter_slot)."""
        self._load_connection_settings()

    def _save_connection_settings(self):
        self._link().set_connection(self.host_edit.text(), self.token_edit.text())

    def _request(self, path: str, timeout: float = 4.0, method: str = "GET", data=None, raw: bool = False,
                 content_type: str = None):
        """The shared link's request(); last_error_detail mirrored here for
        the callers that read it off the panel."""
        link = self._link()
        # The edits on this panel are the truth while it is open - a
        # just-typed address works before focus leaves the field.
        link.set_connection(self.host_edit.text(), self.token_edit.text())
        result = link.request(path, timeout=timeout, method=method, data=data, raw=raw, content_type=content_type)
        self.last_error_detail = link.last_error_detail
        return result

    def _test_connection(self):
        self.status_label.setText(tr("controller.status_testing"))
        QApplication.processEvents()
        ok, result = self._request("/api/v1/health")
        if ok:
            self.status_label.setText(tr("controller.status_ok"))
        else:
            self.status_label.setText(tr("controller.status_failed", reason=result))
        self._refresh_logic_state(reachable=ok)

    def _refresh_logic_state(self, reachable: bool):
        """The logic program's own state, from /api/v1/logic - read-only
        and unauthenticated there, so this needs no token even when the
        connection has none yet. An older controller (no such endpoint)
        simply reports unknown rather than an error: this panel's job is
        to say what it can see, not to fail over a missing extra."""
        if not reachable:
            self.logic_label.setText(tr("controller.logic_unknown"))
            return
        ok, status = self._request("/api/v1/logic")
        if not ok or not isinstance(status, dict):
            self.logic_label.setText(tr("controller.logic_unknown"))
            return
        if not status.get("configured"):
            self.logic_label.setText(tr("controller.logic_none"))
        elif status.get("running"):
            self.logic_label.setText(tr(
                "controller.logic_running",
                blocks=status.get("block_count", 0), cycle=status.get("cycle_time_ms", 0),
                scans=status.get("scan_count", 0), longest=f"{status.get('max_scan_ms', 0.0):.1f}",
                outputs=len(status.get("driven_outputs", [])),
            ))
        elif status.get("loaded"):
            self.logic_label.setText(tr("controller.logic_stopped"))
        else:
            self.logic_label.setText(tr("controller.logic_failed", reason=status.get("last_error") or ""))

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

    # -- Nastawy sterownika na żywo ------------------------------------------------

    def _fetch_settings(self):
        ok, result = self._request("/api/v1/project/settings")
        if not ok or not isinstance(result, dict):
            self._remote_settings = None
            self.settings_status_label.setText(tr("controller.settings_status_failed", reason=result))
            self._settings_timer.stop()
            self.settings_live_check.setChecked(False)
            self._render_settings()
            return
        self._remote_settings = result
        self._render_settings()

    def _toggle_live_settings(self, checked: bool):
        if checked:
            self._fetch_settings()
            if self._remote_settings is not None:
                self._settings_timer.start()
        else:
            self._settings_timer.stop()

    def settings_rows(self) -> list:
        """[(path, studio value, controller value, differs)] for the last
        fetched controller settings against the project as it is now."""
        remote = (self._remote_settings or {}).get("settings") or {}
        local = settings_snapshot(self._studio_window._project)
        rows = []
        for path in sorted(set(local) | set(remote)):
            mine, theirs = local.get(path), remote.get(path)
            rows.append((path, mine, theirs, mine != theirs or (path in local) != (path in remote)))
        return rows

    def _render_settings(self):
        rows = self.settings_rows() if self._remote_settings is not None else []
        differing = [r for r in rows if r[3]]
        shown = differing if self.settings_diff_only_check.isChecked() else rows
        self.settings_table.setRowCount(0)
        for path, mine, theirs, differs in shown:
            row = self.settings_table.rowCount()
            self.settings_table.insertRow(row)
            cells = [QTableWidgetItem(path), QTableWidgetItem("" if mine is None else str(mine)),
                     QTableWidgetItem("" if theirs is None else str(theirs))]
            for col, item in enumerate(cells):
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if differs:
                    item.setBackground(_DIFF_BG)
                self.settings_table.setItem(row, col, item)
        self.take_settings_button.setEnabled(bool(differing))
        if self._remote_settings is None:
            return
        remote = self._remote_settings
        local_hash = settings_hash(self._studio_window._project)
        same = remote.get("settings_hash") == local_hash
        self.settings_status_label.setText(tr(
            "controller.settings_status_same" if same else "controller.settings_status_differ",
            revision=remote.get("revision"), modified_by=remote.get("modified_by") or "?",
            local_revision=self._studio_window._project.revision, count=len(differing)))

    def _take_controller_settings(self):
        """Writes the controller's values into the project (the operator
        changed them on the panel; the project should say the same)."""
        rows = [r for r in self.settings_rows() if r[3] and r[2] is not None]
        if not rows:
            return
        answer = QMessageBox.question(self, tr("controller.take_settings"),
                                      tr("controller.take_settings_confirm", count=len(rows)),
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                      QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        applied = apply_settings_snapshot(self._studio_window._project, {path: theirs for path, _m, theirs, _d in rows})
        self._studio_window._on_project_changed()
        refresh = getattr(self._studio_window, "_refresh_all_project_panels", None)
        if callable(refresh):
            refresh()
        self._render_settings()
        QMessageBox.information(self, tr("controller.take_settings"), tr("controller.take_settings_done", count=len(applied)))

    # -- what stays on the controller (controller.local.json) ----------------------------

    @staticmethod
    def _flatten(value, prefix=""):
        if isinstance(value, dict):
            out = []
            for key in sorted(value):
                out.extend(ControllerPanel._flatten(value[key], f"{prefix}{key}/"))
            return out
        return [(prefix.rstrip("/"), value)]

    def local_settings_rows(self) -> list:
        """[(setting path, value)] of the last GET /api/v1/controller/settings."""
        if not self._local_settings:
            return []
        rows = self._flatten(self._local_settings.get("settings") or {})
        return [(path, value if isinstance(value, str) else json.dumps(value, ensure_ascii=False))
                for path, value in rows]

    def _fetch_local_settings(self):
        ok, result = self._request("/api/v1/controller/settings")
        if not ok or not isinstance(result, dict):
            self._local_settings = None
            self.local_table.setRowCount(0)
            self.local_status_label.setText(tr("controller.local_status_failed", reason=result))
            return
        self._local_settings = result
        rows = self.local_settings_rows()
        self.local_table.setRowCount(0)
        for path, value in rows:
            row = self.local_table.rowCount()
            self.local_table.insertRow(row)
            self.local_table.setItem(row, 0, QTableWidgetItem(path))
            self.local_table.setItem(row, 1, QTableWidgetItem(value))
        self.local_status_label.setText(tr("controller.local_status", source=result.get("source") or "?",
                                           language=result.get("language") or "?", count=len(rows)))

    # -- switching counters ------------------------------------------------------------

    def counter_rows(self) -> list:
        """[(tag, closes, opens, closed_seconds, threshold)] of the last fetch."""
        counters = (self._remote_counters or {})
        return [(tag, int(rec.get("closes", 0)), int(rec.get("opens", 0)), float(rec.get("closed_seconds", 0.0)),
                 rec.get("warning_threshold")) for tag, rec in sorted(counters.items())]

    def _fetch_counters(self):
        ok, result = self._request("/api/v1/counters")
        if not ok or not isinstance(result, dict):
            self._remote_counters = None
            self.counters_table.setRowCount(0)
            self.counters_status_label.setText(tr("controller.counters_status_failed", reason=result))
            self.reset_counter_button.setEnabled(False)
            self.reset_all_counters_button.setEnabled(False)
            return
        if not result.get("available"):
            self._remote_counters = None
            self.counters_table.setRowCount(0)
            self.counters_status_label.setText(tr("controller.counters_unavailable"))
            self.reset_counter_button.setEnabled(False)
            self.reset_all_counters_button.setEnabled(False)
            return
        self._remote_counters = dict(result.get("counters") or {})
        selected = self._selected_counter_tag()
        self.counters_table.setRowCount(0)
        for tag, closes, opens, closed_seconds, threshold in self.counter_rows():
            row = self.counters_table.rowCount()
            self.counters_table.insertRow(row)
            cells = (tag, str(closes), str(opens), _format_duration(closed_seconds),
                     "" if threshold is None else str(threshold))
            for col, value in enumerate(cells):
                self.counters_table.setItem(row, col, QTableWidgetItem(value))
            if tag == selected:
                self.counters_table.selectRow(row)
        self.counters_status_label.setText(tr("controller.counters_status", count=self.counters_table.rowCount()))
        self.reset_counter_button.setEnabled(self.counters_table.rowCount() > 0)
        self.reset_all_counters_button.setEnabled(self.counters_table.rowCount() > 0)

    def _selected_counter_tag(self):
        row = self.counters_table.currentRow()
        item = self.counters_table.item(row, 0) if row >= 0 else None
        return item.text() if item is not None else None

    def _reset_counter(self, tag: str):
        ok, result = self._request(f"/api/v1/counters/{tag}/reset", method="POST", timeout=8.0)
        return ok, result

    def _reset_selected_counter(self):
        tag = self._selected_counter_tag()
        if not tag:
            QMessageBox.information(self, tr("controller.reset_counter"), tr("controller.reset_select_row"))
            return
        answer = QMessageBox.question(self, tr("controller.reset_counter"), tr("controller.reset_confirm", tag=tag),
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                      QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        ok, result = self._reset_counter(tag)
        if not ok:
            QMessageBox.warning(self, tr("controller.reset_counter"), tr("controller.reset_failed", tag=tag, reason=result))
        self._fetch_counters()
        if ok:
            self.counters_status_label.setText(tr("controller.reset_done", count=1))

    def _reset_all_counters(self):
        tags = [row[0] for row in self.counter_rows()]
        if not tags:
            return
        answer = QMessageBox.question(self, tr("controller.reset_all_counters"),
                                      tr("controller.reset_all_confirm", count=len(tags)),
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                      QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        failed = []
        for tag in tags:
            ok, result = self._reset_counter(tag)
            if not ok:
                failed.append((tag, result))
        self._fetch_counters()
        if failed:
            QMessageBox.warning(self, tr("controller.reset_all_counters"),
                                tr("controller.reset_failed", tag=failed[0][0], reason=failed[0][1]))
        self.counters_status_label.setText(tr("controller.reset_done", count=len(tags) - len(failed)))

    # -- Wyślij do urządzenia ------------------------------------------------------

    def _send_to_device(self):
        """The file on disk is what goes to the controller - so the project
        is saved first (with the editors' documents inside), then the
        controller's header is read and compared, then the bytes are
        posted with the controller's revision as the guard."""
        win = self._studio_window
        path = getattr(win, "_project_path", None)
        editors_dirty = getattr(win, "_editors_dirty", lambda: False)()
        if path is None or win._project.is_dirty or editors_dirty:
            answer = QMessageBox.question(self, tr("controller.send_to_device"), tr("controller.send_needs_save"),
                                          QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                          QMessageBox.StandardButton.Yes)
            if answer != QMessageBox.StandardButton.Yes or not win._save_project():
                return
            path = win._project_path
        try:
            local = load_project(path)
            payload = Path(path).read_bytes()
        except (ProjectFormatError, OSError) as exc:
            QMessageBox.warning(self, tr("controller.send_to_device"), str(exc))
            return

        ok, header = self._request("/api/v1/project")
        if not ok:
            QMessageBox.warning(self, tr("controller.send_to_device"), tr("controller.send_failed", reason=header))
            return
        controller_revision = header.get("revision")
        if header.get("loaded") and header.get("settings_hash") and header["settings_hash"] != settings_hash(local):
            ok, remote = self._request("/api/v1/project/settings")
            remote_settings = remote.get("settings", {}) if ok and isinstance(remote, dict) else {}
            diff = settings_diff(settings_snapshot(local), remote_settings)
            if not self._confirm_overwrite(header, local, diff):
                return

        query = f"?expected_revision={int(controller_revision)}" if isinstance(controller_revision, int) else ""
        ok, result = self._request("/api/v1/project/install" + query, method="POST", data=payload,
                                   content_type="application/gzip", timeout=30.0)
        if not ok:
            detail = self.last_error_detail
            if isinstance(detail, dict) and detail.get("error") == "revision_mismatch":
                controller = detail.get("controller") or {}
                message = tr("controller.send_conflict_moved", revision=controller.get("revision"),
                             modified_by=controller.get("modified_by"))
            elif isinstance(detail, dict) and detail.get("error") == "project_refused":
                reason = detail.get("reason") or {}
                message = tr("controller.send_refused", reason=reason.get("text") or str(reason))
            else:
                message = tr("controller.send_failed", reason=result)
            QMessageBox.warning(self, tr("controller.send_to_device"), message)
            return
        # Three real outcomes, not two: the controller rebuilt itself
        # from the project (the normal one now), it is restarting onto
        # it, or the file is waiting for its next start.
        reloaded = result.get("reloaded") or {}
        if reloaded.get("success"):
            key = "controller.send_done_reloaded"
        elif result.get("restart_scheduled"):
            key = "controller.send_done"
        else:
            key = "controller.send_done_no_restart"
        self.status_label.setText(tr("controller.status_sent", revision=result.get("revision")))
        QMessageBox.information(self, tr("controller.send_to_device"), tr(key, revision=result.get("revision")))

    def _confirm_overwrite(self, header: dict, local, diff: list) -> bool:
        """SPEC "Wersjonowanie": the controller's settings are not the
        project's - show every difference and let the operator decide.
        Returns True to send anyway."""
        dialog = SettingsDiffDialog(header, local, diff, self)
        return dialog.exec() == QDialog.DialogCode.Accepted

    # -- Zgraj z urządzenia -----------------------------------------------------------

    def _receive_from_device(self):
        """GET /api/v1/project/file (Engineer token) -> a file the operator
        names -> opened as the project, exactly like File > Open."""
        win = self._studio_window
        if not win._confirm_discard_project():
            return
        ok, payload = self._request("/api/v1/project/file", raw=True, timeout=30.0)
        if not ok:
            QMessageBox.warning(self, tr("controller.receive_from_device"), tr("controller.receive_failed", reason=payload))
            return
        start_dir = win.settings.value("project/last_dir", "")
        suggested = str(Path(start_dir) / "projekt.epw") if start_dir else "projekt.epw"
        path, _filter = QFileDialog.getSaveFileName(self, tr("controller.receive_save_title"), suggested,
                                                    "EPW Project (*.epw)")
        if not path:
            return
        if not path.lower().endswith(".epw"):
            path += ".epw"
        try:
            Path(path).write_bytes(payload)
        except OSError as exc:
            QMessageBox.warning(self, tr("controller.receive_from_device"), str(exc))
            return
        win._load_project_from_path(path)
        self.status_label.setText(tr("controller.status_received", revision=win._project.revision))


class SettingsDiffDialog(QDialog):
    """What differs between the project about to be sent and the
    controller's own settings (SPEC "Wersjonowanie": "pokazać, co się
    rozjechało (tu 25 A, tam 40 A), zamiast nadpisać")."""

    def __init__(self, header: dict, local, diff: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("controller.send_conflict_title"))
        self.resize(720, 420)
        layout = QVBoxLayout(self)
        intro = QLabel(tr("controller.send_conflict_text", controller_revision=header.get("revision"),
                          modified_by=header.get("modified_by") or "?", local_revision=local.revision,
                          count=len(diff)))
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.table = QTableWidget(len(diff), 3)
        self.table.setHorizontalHeaderLabels([tr("controller.diff_col_setting"), tr("controller.diff_col_studio"),
                                              tr("controller.diff_col_controller")])
        _prep_table(self.table)
        _make_column_resizable(self.table, 0, 360)
        for row, (path, mine, theirs) in enumerate(diff):
            self.table.setItem(row, 0, QTableWidgetItem(path))
            self.table.setItem(row, 1, QTableWidgetItem("" if mine is None else str(mine)))
            self.table.setItem(row, 2, QTableWidgetItem("" if theirs is None else str(theirs)))
        layout.addWidget(self.table, 1)
        buttons = QDialogButtonBox()
        send = buttons.addButton(tr("controller.send_anyway"), QDialogButtonBox.ButtonRole.AcceptRole)
        cancel = buttons.addButton(tr("controller.cancel"), QDialogButtonBox.ButtonRole.RejectRole)
        send.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        layout.addWidget(buttons)


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

        # A tree, not a flat list: with 27 topics a single column of
        # titles stops being navigable, and the chapters ("Start",
        # "Projekt", "Sterownik"...) are also the order somebody reads
        # them in for the first time.
        self.topic_tree = QTreeWidget()
        self.topic_tree.setHeaderHidden(True)
        self.topic_tree.setFixedWidth(260)
        self.topic_tree.currentItemChanged.connect(self._on_tree_item_changed)
        splitter.addWidget(self.topic_tree)

        self.viewer = QTextBrowser()
        self.viewer.setOpenExternalLinks(False)
        # help://key cross-references between topics, resolved here -
        # this help is offline and has no business reaching the network
        # (the same scheme, and the same reason, as EPW-OS's own
        # help_window.py).
        self.viewer.anchorClicked.connect(self._on_anchor_clicked)
        splitter.addWidget(self.viewer)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

        self._topics = []
        self._items = {}
        self.refresh()

    def refresh(self):
        from studio.shell.i18n import get_language
        from studio.shell.help._manifest import CHAPTERS, TOPICS

        current_key = self._current_key()
        self._topics = TOPICS
        self._lang = get_language()
        title_index = 1 if self._lang == "pl" else 2

        self.topic_tree.blockSignals(True)
        self.topic_tree.clear()
        self._items = {}
        chapter_items = {}
        for chapter_key, chapter_pl, chapter_en in CHAPTERS:
            item = QTreeWidgetItem([chapter_pl if self._lang == "pl" else chapter_en])
            font = item.font(0)
            font.setBold(True)
            item.setFont(0, font)
            # A chapter is a heading, not a destination - selecting one
            # would leave the viewer with nothing to show.
            item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            chapter_items[chapter_key] = item
        for entry in self._topics:
            key, chapter = entry[0], entry[3]
            leaf = QTreeWidgetItem([entry[title_index]])
            leaf.setData(0, Qt.ItemDataRole.UserRole, key)
            chapter_items[chapter].addChild(leaf)
            self._items[key] = leaf
        for chapter_key, _pl, _en in CHAPTERS:
            item = chapter_items[chapter_key]
            if item.childCount():
                self.topic_tree.addTopLevelItem(item)
        self.topic_tree.expandAll()
        self.topic_tree.blockSignals(False)

        self._show(current_key if current_key in self._items else self._topics[0][0])

    def _current_key(self):
        item = self.topic_tree.currentItem() if self._items else None
        return item.data(0, Qt.ItemDataRole.UserRole) if item is not None else None

    def _on_tree_item_changed(self, current, _previous):
        key = current.data(0, Qt.ItemDataRole.UserRole) if current is not None else None
        if key is not None:
            self.viewer.setMarkdown(load_help_topic_markdown(key, self._lang))

    def _show(self, key: str):
        item = self._items.get(key)
        if item is None:
            return
        self.topic_tree.setCurrentItem(item)
        # setCurrentItem() on an already-current item emits nothing, so
        # the viewer is filled here rather than relying on the signal.
        self.viewer.setMarkdown(load_help_topic_markdown(key, self._lang))

    def _on_anchor_clicked(self, url):
        if url.scheme() == "help":
            self.select_topic(url.host() or url.path().lstrip("/"))

    def select_topic(self, key: str):
        """Task 5.3 (pomoc kontekstowa, F1) - jumps straight to `key`
        instead of making the caller know this panel's own row-index
        bookkeeping. A silent no-op for an unknown key (same "don't
        crash over a lookup miss" stance _on_topic_selected() above
        already has for a missing .md file) rather than raising -
        _HELP_TOPIC_BY_TREE_KEY in main_window.py is a hand-maintained
        map that could in principle name a topic not in TOPICS."""
        self._show(key)


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
    card_by_id = {c.id: c for c in project.cards}
    location_codes = {loc.code for loc in project.locations}

    def _address_card_and_kind(address):
        """(card_id, kind) from `address`, tolerant of a malformed one -
        try_parse_address() (not parse_address()) because `address` here
        comes from a device's own feedback/command list, user-editable
        text that IS legitimately allowed to be malformed (that's
        exactly what check 1 below flags), unlike a Point's own always-
        machine-generated address elsewhere in this module."""
        parsed = try_parse_address(address)
        if parsed:
            return parsed[0], parsed[1]
        return (address.split(".", 1)[0] if "." in address else address), None

    def _card_exists_for(address):
        # A card can have more than one kind now (task follow-up, user
        # report: "karta ELA1 ma DI oraz AI") - "the card still exists"
        # has to mean it exists AND still has the exact kind this
        # address names, not just a matching id: a device pointing at
        # "ELA1.AI.3" is NOT covered by an ELA1 card that only has DI.
        card_id, kind = _address_card_and_kind(address)
        card = card_by_id.get(card_id)
        return card is not None and kind in card.channel_kinds

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
            elif not _card_exists_for(address):
                issues.append(ValidationIssue(
                    "error",
                    tr(
                        "validation.msg_device_point_deleted_card",
                        device=device.id, address=address, card=_address_card_and_kind(address)[0],
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

    # 4) "punkt z lokalizacją, której nie ma na liście" - the RESOLVED
    # (inherited-or-explicit) location, task "jedno źródło listy kart"
    # 3.4: a card's own now-stale location must surface here exactly
    # the same way a point's own stale explicit one always did.
    for point in project.points:
        card_id, _kind = _address_card_and_kind(point.address)
        card = card_by_id.get(card_id)
        resolved = effective_location(point, card)
        if resolved and resolved not in location_codes:
            issues.append(ValidationIssue(
                "warning",
                tr("validation.msg_point_unknown_location", address=point.address, location=resolved),
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

    # 8) Task "wyłącznik jednocewkowy bistabilny" - a SWITCHED apparatus
    # whose command style can't be executed honestly: a pulsed style
    # with no pulse time, or a single-coil impulse relay (PULSE_TOGGLE)
    # with no feedback (every pulse toggles - without knowing the
    # current state the runtime would flip it the wrong way) or with
    # more than two outputs. Mirrors runtime's apparatus_command_
    # definitions(), which refuses exactly these and logs instead of
    # guessing - better to see it here, before upload.
    for device in project.devices:
        if device.behavior != "SWITCHED" or not device.command:
            continue
        if device.command_style in _PULSED_STYLES and not (device.pulse_ms and device.pulse_ms > 0):
            issues.append(ValidationIssue(
                "error",
                tr("validation.msg_device_pulse_missing_ms", device=device.id, style=device.command_style),
                "devices", "select_device", device.id,
            ))
        if device.command_style == "PULSE_TOGGLE":
            if not device.feedback:
                issues.append(ValidationIssue(
                    "error",
                    tr("validation.msg_device_toggle_needs_feedback", device=device.id),
                    "devices", "select_device", device.id,
                ))
            if len(device.command) > 2:
                issues.append(ValidationIssue(
                    "error",
                    tr("validation.msg_device_toggle_too_many_outputs", device=device.id, n=len(device.command)),
                    "devices", "select_device", device.id,
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


def _id_prefix_for_model(model: str) -> str:
    """User report #2: id was a blank field ("KARTA1"/"KARTA2", nothing
    to do with the actual module) - "ELA01" -> "ELA", "ADA01" -> "ADA",
    "EPM" -> "EPM" (nothing to strip). The id itself stays free text the
    user can still overwrite (CardsPanel._on_card_item_changed's own
    "_id_is_auto" tracking) - this only supplies the SUGGESTION's
    prefix. Falls back to the old generic "KARTA" placeholder for a
    still-empty model.

    User report 3.2: the suggestion is inserted directly (bypasses the
    _on_card_item_changed manual-typing checks, since it's set while
    signals are blocked) - so dots/spaces are stripped from the MODEL
    text here too, or a model like "ELA 01.rev2" could hand back a
    prefix that breaks the address grammar just as badly as a hand-typed
    one would."""
    model = re.sub(r"[.\s]+", "", (model or "")).strip().upper()
    if not model:
        return "KARTA"
    return model.rstrip("0123456789") or model


def _next_free_modbus_unit_id(project, exclude_card=None):
    """User report #3: "karta bez adresu jednostki nie odezwie się na
    magistrali" - every new card gets a real, working default instead
    of a silent None. Returns None only once the entire 1-247 range is
    already taken by other cards - a real "nothing left" state, not
    expected in practice, left for _style_modbus_item() to show
    visibly rather than as blank text."""
    used = {c.modbus_unit_id for c in project.cards if c is not exclude_card and c.modbus_unit_id is not None}
    for n in range(1, 248):
        if n not in used:
            return n
    return None


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
