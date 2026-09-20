from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QLineEdit,
)
from PySide6.QtGui import QDrag
from PySide6.QtCore import Qt, QMimeData

from logic_studio.i18n import tr
from logic_studio.ui.icons import block_icon

TYPE_ID_ROLE = Qt.UserRole
ADDRESS_ROLE = Qt.UserRole + 1

DRAG_THRESHOLD_PX = 4


class DeviceTree(QTreeWidget):
    """Drag-and-drop for a device address leaf, straight onto the canvas —
    same manual, distance-thresholded drag as LibraryTree
    (ui/panels/library.py), kept as its own small class rather than shared
    because this one also carries an address alongside the type_id in the
    drag payload (see mouseMoveEvent): dropping ELA01.DI06 here creates an
    already-configured input.di block instead of a blank one that still
    needs its Address set by hand in the property grid.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(False)  # driven manually below, like LibraryTree
        self._press_pos = None
        self._press_item = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            item = self.itemAt(event.pos())
            if item and item.data(0, TYPE_ID_ROLE):
                self._press_pos = event.pos()
                self._press_item = item
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._press_item and (event.buttons() & Qt.LeftButton) and self._press_pos is not None:
            if (event.pos() - self._press_pos).manhattanLength() > DRAG_THRESHOLD_PX:
                item = self._press_item
                self._press_item = None
                self._press_pos = None

                type_id = item.data(0, TYPE_ID_ROLE)
                address = item.data(0, ADDRESS_ROLE) or ""

                drag = QDrag(self)
                mime = QMimeData()
                # "type_id|address" — LogicView.dropEvent() splits this back
                # apart; plain type_id (no "|") still works for anything
                # that drags from here without an address one day.
                mime.setText(f"{type_id}|{address}" if address else type_id)
                drag.setMimeData(mime)
                drag.setPixmap(block_icon(type_id, size=24).pixmap(24, 24))
                drag.exec(Qt.CopyAction)
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._press_pos = None
        self._press_item = None
        super().mouseReleaseEvent(event)


class DeviceExplorerPanel(QWidget):
    """Lists the IO addresses this build actually knows about: the fixed
    DI/DO channels from DeviceModel, and the project's dynamic analog points
    (AUDIT_REPORT.md §7) — rebuilt via set_project() whenever the project (or
    its analog_points setting) changes. No EPM branch: that comes back once
    EPM measurement blocks exist to back it.

    Every address leaf is draggable straight onto the canvas as an
    already-configured DI/DO/AI/AO block (feat/block-rendering-library,
    follow-up request).
    """
    def __init__(self, project=None, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # feat/library-recent-and-search: a search box, for the same
        # reason the block library has one — this tree lists EVERY
        # channel of every card, which is 64 rows per ELA before the
        # project has any analog points at all. Scrolling to ELA01.DI47
        # is slower than typing "47", and with two or three cards it is
        # slower than opening the cabinet and reading the label.
        #
        # Deliberately the same behaviour as LibraryPanel's own box
        # (ui/panels/library.py): it hides what does not match, keeps a
        # branch visible only while something in it does, and expands
        # whatever still has results — results left inside a collapsed
        # branch look like no results at all.
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText(tr("device.search"))
        self.search_box.setClearButtonEnabled(True)
        self.search_box.textChanged.connect(self._filter_tree)
        layout.addWidget(self.search_box)

        self.tree = DeviceTree()
        self.tree.setHeaderLabels([tr("device.header")])
        layout.addWidget(self.tree)

        self.project = project
        self._build_tree()

    def set_project(self, project):
        """Rebind to a (possibly new) project and rebuild the Analog branch.
        Call whenever the project is swapped (new/open/undo/redo) or its
        analog_points setting changes (Project Settings dialog)."""
        self.project = project
        self._build_tree()

    def _build_tree(self):
        from logic_studio.core.device_model import DeviceModel

        self.tree.clear()

        # Root node
        root = QTreeWidgetItem(self.tree, ["EPW Controller"])
        root.setExpanded(True)

        # feat/multi-device-io: one branch PER DEVICE the project actually
        # defines rather than a single hardcoded "ELA-01"/"ADA-01" — a
        # project with ELA01+ELA02 gets two separate, independently-
        # expandable Input Module branches. Task "jedno źródło listy kart":
        # the device list AND each device's own channel count now come
        # from get_ela_device_channels()/get_ada_device_channels() - when
        # Studio's real Cards are bridged in (LogicPanel), different cards
        # can have different channel counts, so this can no longer use one
        # shared count for every branch the way get_ela_channels() alone
        # would (see DeviceModel's own module docstring).
        ela_pairs = DeviceModel.get_ela_device_channels(self.project)
        for dev, channels in ela_pairs:
            ela_module = QTreeWidgetItem(root, [f"{dev} (Input Module / Acquisition)"])
            ela_module.setExpanded(True)
            for i in range(1, channels + 1):
                addr = DeviceModel.format_ela_address(dev, i)
                self._add_leaf(ela_module, addr, "input.di", addr)

        ada_pairs = DeviceModel.get_ada_device_channels(self.project)
        for dev, channels in ada_pairs:
            ada_module = QTreeWidgetItem(root, [f"{dev} (Output Module / Actuator)"])
            ada_module.setExpanded(True)
            for i in range(1, channels + 1):
                addr = DeviceModel.format_ada_address(dev, i)
                self._add_leaf(ada_module, addr, "output.do", addr)

        # Task "jedno źródło listy kart" 1.3: no ELA/ADA card at all (a
        # brand-new standalone project, or an embedded one whose Studio
        # project genuinely has no I/O cards yet) is now a real, correct
        # state (see DeviceModel's own docstring - no more silent
        # "ELA01"/"ADA01"). Say so plainly instead of showing a tree that
        # just... has nothing under "EPW Controller", which reads as a
        # bug, not as "go add a card". No i18n here (see module note
        # below) - matches the rest of this tree's own hardcoded strings,
        # Logic Studio has no tr()/i18n mechanism at all today (checked;
        # building one is a much larger, separate change, out of this
        # task's own "podłączasz źródło danych, nie przebudowujesz
        # edytorów" scope).
        if not ela_pairs and not ada_pairs:
            hint = QTreeWidgetItem(root, ["No I/O cards — add a card in the project"])
            hint.setDisabled(True)

        # Analog points — fully project-defined, empty tree when the project
        # has none. No example/placeholder entries.
        analog_branch = QTreeWidgetItem(root, ["Analog"])
        analog_branch.setExpanded(True)
        if self.project is not None:
            for point in DeviceModel.get_analog_points(self.project):
                addr = point.get("address", "")
                unit = point.get("unit", "")
                direction = point.get("direction", "")
                label = f"{addr} ({direction}{', ' + unit if unit else ''})"
                type_id = "input.ai" if direction == "input" else "output.ao"
                self._add_leaf(analog_branch, label, type_id, addr)

        # A rebuild makes brand-new, unhidden items, so whatever is typed
        # has to be applied again - otherwise adding a card while a search
        # was active would silently show the whole tree back.
        self._filter_tree()

    # ---- Search ----------------------------------------------------------

    def _filter_tree(self, text=None):
        """Hide every leaf that does not match, and every branch left with
        nothing visible under it.

        Matches the visible LABEL and the ADDRESS both: the label carries
        the direction and unit for an analog point, while the address is
        what is written on the terminal an electrician is looking at.
        Case-insensitive, and dots are ignored on both sides, so "ELA01
        DI06", "ela01.di06" and "eladi" all find the same channel —
        somebody searching for a channel should not have to reproduce the
        punctuation of an address format.
        """
        if text is None:
            text = self.search_box.text()
        needle = self._normalize(text)

        root = self.tree.topLevelItem(0)
        if root is None:
            return

        self._filter_item(root, needle)
        root.setHidden(False)
        if needle:
            root.setExpanded(True)

    def _filter_item(self, item, needle):
        """Returns whether this item (or anything under it) is still
        visible. Depth-first, so a branch's own visibility is decided
        after its children have decided theirs."""
        visible_children = 0
        for i in range(item.childCount()):
            if self._filter_item(item.child(i), needle):
                visible_children += 1

        if item.childCount() > 0:
            # A branch stands or falls by its contents. With no search at
            # all it always stands.
            visible = not needle or visible_children > 0
            item.setHidden(not visible)
            if needle and visible:
                item.setExpanded(True)
            return visible

        # A leaf: matched on its own text and its address.
        address = item.data(0, ADDRESS_ROLE) or ""
        matches = not needle or needle in self._normalize(item.text(0)) or needle in self._normalize(address)
        item.setHidden(not matches)
        return matches

    @staticmethod
    def _normalize(value):
        """Lower-cased, with the separators an address format uses dropped,
        so punctuation never decides whether a search finds a channel."""
        return "".join(ch for ch in str(value).lower() if ch.isalnum())

    def _add_leaf(self, parent, label, type_id, address):
        item = QTreeWidgetItem(parent, [label])
        item.setData(0, TYPE_ID_ROLE, type_id)
        item.setData(0, ADDRESS_ROLE, address)
        item.setIcon(0, block_icon(type_id))
        return item
