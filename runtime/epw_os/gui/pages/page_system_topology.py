from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame, QTreeWidget, QTreeWidgetItem, QTreeWidgetItemIterator, QTableWidget, QTableWidgetItem, QSpacerItem, QSizePolicy, QSplitter
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QBrush
from epw_os.gui.widgets.industrial_labels import StatusLabel
from epw_os.gui.widgets.topology_canvas import TopologyCanvas
from epw_os.gui.table_helpers import set_resizable_columns
from epw_os.i18n import tr

class PageSystemTopology(QWidget):
    def __init__(self, tag_manager, parent=None):
        super().__init__(parent)
        self.tag_manager = tag_manager

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel(tr("nav.system_topology"))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("PageHeader")
        layout.addWidget(title)

        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        # stretch=1 so the splitter eats all remaining vertical space -
        # without it a QVBoxLayout can hand that space to the PageHeader
        # label instead, which then balloons into a big empty navy bar
        # while tree + diagram get squashed at the bottom.
        layout.addWidget(main_splitter, stretch=1)

        # Left Column (Tree + Info Panel) - a vertical splitter, not a plain
        # QVBoxLayout, so the operator can also drag the boundary between
        # the device tree and the info panel to resize their heights
        # (the horizontal main_splitter already gives width control).
        left_splitter = QSplitter(Qt.Orientation.Vertical)

        # Left Tree
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setMinimumWidth(250)
        self.tree.setMinimumHeight(100)

        root = QTreeWidgetItem(self.tree, ["ENTRY GATE"])
        
        pi = QTreeWidgetItem(root, ["EPW Controller"])
        QTreeWidgetItem(pi, ["Protection Engine"])
        QTreeWidgetItem(pi, ["Logic Engine"])
        QTreeWidgetItem(pi, ["Event Recorder"])
        QTreeWidgetItem(pi, ["Communication"])
        QTreeWidgetItem(pi, ["Diagnostics"])

        ela = QTreeWidgetItem(root, ["ELA-01"])
        QTreeWidgetItem(ela, ["Digital Inputs"])
        QTreeWidgetItem(ela, ["Diagnostics"])
        QTreeWidgetItem(ela, ["Firmware"])

        ada = QTreeWidgetItem(root, ["ADA-01"])
        QTreeWidgetItem(ada, ["Digital Outputs"])
        QTreeWidgetItem(ada, ["Diagnostics"])
        QTreeWidgetItem(ada, ["Firmware"])

        epm = QTreeWidgetItem(root, ["EPM-01"])
        QTreeWidgetItem(epm, ["Measurements"])
        QTreeWidgetItem(epm, ["Diagnostics"])
        QTreeWidgetItem(epm, ["Firmware"])

        self.tree.expandAll()
        self.tree.itemSelectionChanged.connect(self.on_tree_selection_changed)
        left_splitter.addWidget(self.tree)

        # Information Panel
        info_frame = QFrame()
        info_frame.setObjectName("SunkenFrame")
        info_frame.setMinimumHeight(180)

        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(5, 5, 5, 5)
        
        self.lbl_info_title = QLabel(tr("pages.system_topology.info_title"))
        self.lbl_info_title.setObjectName("SectionHeader")
        self.lbl_info_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_layout.addWidget(self.lbl_info_title)
        
        self.info_table = QTableWidget(0, 2)
        self.info_table.setHorizontalHeaderLabels([tr("pages.system_topology.col_property"), tr("pages.common.col_value")])
        set_resizable_columns(self.info_table.horizontalHeader(), [170, 240])
        self.info_table.verticalHeader().setVisible(False)
        self.info_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        info_layout.addWidget(self.info_table)
        left_splitter.addWidget(info_frame)

        # Tree gets roughly 2x the info panel's height by default, but the
        # operator can drag the handle between them to any split they like.
        left_splitter.setSizes([400, 200])
        left_splitter.setStretchFactor(0, 2)
        left_splitter.setStretchFactor(1, 1)
        left_splitter.setCollapsible(0, False)
        left_splitter.setCollapsible(1, False)

        main_splitter.addWidget(left_splitter)

        # Right Diagram
        self.canvas = TopologyCanvas()
        # Task: podpowiedzi - "wskazniki stanu i kolorowe oznaczenia".
        # One tooltip for the whole hand-drawn canvas (RX/TX LEDs and
        # node status colors are painted pixels, not separate widgets a
        # per-element tooltip could attach to) rather than none at all.
        self.canvas.setToolTip(tr("pages.system_topology.tooltip_canvas"))
        self.canvas.node_selected.connect(self.on_diagram_clicked)
        
        main_splitter.addWidget(self.canvas)
        main_splitter.setSizes([320, 700])
        # Extra width from a wider window goes mostly to the diagram.
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 3)
        main_splitter.setCollapsible(0, False)
        main_splitter.setCollapsible(1, False)

        # Node status (top-level ONLINE/OFFLINE, both the diagram's status
        # chip and the info table's "Status" row) is wired to the exact
        # same live source as the Main View Device Status panel
        # (DeviceStatusPanel in page_entry_gate.py) - the Device.*.Status
        # tags DeviceManager/EPWCore keep real. Everything ELSE in
        # sim_data below (CPU Load, Frames RX/TX, Serial Number,
        # Temperature, per-subsystem statuses...) has no corresponding
        # tag anywhere in the system and stays a clearly-fabricated
        # placeholder - see SESSION_REPORT.md's WYMAGA DECYZJI section
        # rather than inventing fake-but-plausible telemetry.
        #
        # "EPM-01" is the one node without a name-matching Device.*.Status
        # tag - Device.Modbus.Status is the closest real thing (EPM-01 is
        # this project's Modbus-connected power meter in the default
        # device set) but it's a protocol/channel status, not literally
        # "is EPM-01 itself online". Flagged as WYMAGA DECYZJI too.
        self._device_status_tags = {
            "EPW Controller": "Device.OrangePi.Status",
            "ELA-01": "Device.ELA01.Status",
            "ADA-01": "Device.ADA01.Status",
            "EPM-01": "Device.Modbus.Status",
        }
        self.tag_manager.tag_changed.connect(self._on_device_status_tag_changed)
        self._seed_device_statuses()

        # Task (Part 3b): every field below except "Status" (live-overridden
        # in on_tree_selection_changed(), see the comment above
        # _device_status_tags) and "Device" (just repeats the node's own
        # name, not fabricated telemetry) used to hold a permanently
        # hardcoded, plausible-looking number (CPU Load, Temperature,
        # Frames RX/TX, Serial Number, ...) with no live source anywhere
        # in the system - indistinguishable on screen from real
        # diagnostics. NO_DATA replaces every one of those: an operator
        # sees plainly that nothing is behind the field, instead of a
        # number that looks measured. The dict is still named sim_data and
        # still keyed the same way on purpose - see on_tree_selection_changed(),
        # which cross-references these exact keys/names elsewhere in this
        # file and in topology_canvas.py.
        NO_DATA = tr("pages.system_topology.no_data")
        self.sim_data = {
            "EPW Controller": {
                "Status": "RUNNING",
                "CPU Load": NO_DATA,
                "Memory Usage": NO_DATA,
                "Communication Threads": NO_DATA,
                "Protection Engine Status": NO_DATA,
                "Logic Engine Status": NO_DATA,
                "Event Recorder Status": NO_DATA,
                "Database Status": NO_DATA,
                "Runtime": NO_DATA,
                "Temperature": NO_DATA
            },
            "ELA-01": {
                "Device": "ELA-01",
                "Status": "ONLINE",
                "Firmware": NO_DATA,
                "Hardware Revision": NO_DATA,
                "Serial Number": NO_DATA,
                "Communication": NO_DATA,
                "Supply Voltage": NO_DATA,
                "Temperature": NO_DATA,
                "Frames RX": NO_DATA,
                "Frames TX": NO_DATA,
                "CRC Errors": NO_DATA,
                "Timeouts": NO_DATA,
                "Last Communication": NO_DATA,
                "Simulation State": NO_DATA
            },
            "ADA-01": {
                "Device": "ADA-01",
                "Status": "ONLINE",
                "Firmware": NO_DATA,
                "Hardware Revision": NO_DATA,
                "Serial Number": NO_DATA,
                "Communication": NO_DATA,
                "Supply Voltage": NO_DATA,
                "Temperature": NO_DATA,
                "Frames RX": NO_DATA,
                "Frames TX": NO_DATA,
                "CRC Errors": NO_DATA,
                "Timeouts": NO_DATA,
                "Last Communication": NO_DATA,
                "Simulation State": NO_DATA
            },
            "EPM-01": {
                "Device": "EPM-01",
                "Status": "ONLINE",
                "Firmware": NO_DATA,
                "Hardware Revision": NO_DATA,
                "Serial Number": NO_DATA,
                "Communication": NO_DATA,
                "Supply Voltage": NO_DATA,
                "Temperature": NO_DATA,
                "Frames RX": NO_DATA,
                "Frames TX": NO_DATA,
                "CRC Errors": NO_DATA,
                "Timeouts": NO_DATA,
                "Last Communication": NO_DATA,
                "Simulation State": NO_DATA
            }
        }

        # Default selection
        self.tree.setCurrentItem(pi)

    def _seed_device_statuses(self):
        """Read each Device.*.Status tag's *current* value directly,
        rather than relying solely on a future tag_changed event - the
        same 'seed from current value, don't just wait for a signal'
        pattern used to fix the Main View Device Status panel's identical
        bug (a one-shot ONLINE transition can fire on SimulatorDriver's
        background thread before this page even exists, and would
        otherwise be missed forever)."""
        for key, tag in self._device_status_tags.items():
            value = self.tag_manager.get_value(tag)
            if value is not None:
                self._apply_device_status(key, value, "GOOD")

    def _on_device_status_tag_changed(self, tag_name, value, quality):
        for key, tag in self._device_status_tags.items():
            if tag == tag_name:
                self._apply_device_status(key, value, quality)
                return

    def _apply_device_status(self, node_key, value, quality):
        node = next((n for n in self.canvas.nodes if n.key == node_key), None)
        if node is None:
            return
        # Same OFFLINE-on-bad-quality rule as DeviceStatusPanel.update_label
        # in page_entry_gate.py, for consistency between the two views.
        node.status = "OFFLINE" if (quality == "BAD" or value == "OFFLINE") else value
        self.canvas.update()
        # If this node's details happen to be the ones on screen right
        # now, refresh the info table's Status row too instead of leaving
        # it showing a stale value until the operator reselects the node.
        selected = self.tree.selectedItems()
        if selected and node_key in selected[0].text(0):
            self.on_tree_selection_changed()

    def on_diagram_clicked(self, name):
        # Find matching node in tree and select it (this will trigger on_tree_selection_changed)
        iterator = QTreeWidgetItemIterator(self.tree)
        while iterator.value():
            item = iterator.value()
            if name in item.text(0):
                self.tree.setCurrentItem(item)
                return
            iterator += 1

    def on_tree_selection_changed(self):
        items = self.tree.selectedItems()
        if not items:
            return
            
        node_name = items[0].text(0)
        # node_name itself (device/subsystem name) is intentionally left
        # untranslated - see SESSION_REPORT.md: it's cross-referenced by
        # exact-string matching against the tree, the diagram canvas node
        # keys/names, and self.sim_data's dict keys, so translating it
        # would require touching matching logic in this file and in
        # topology_canvas.py, which is out of this task's scope.
        self.lbl_info_title.setText(tr("pages.system_topology.info_title_for", name=node_name.upper()))
        
        # Highlight diagram widget
        for n in self.canvas.nodes:
            n.selected = (n.name in node_name or n.key in node_name)
        self.canvas.update()
        
        # Fallback to ELA-01, ADA-01, EPM-01 prefix matching
        lookup_key = None
        for k in self.sim_data.keys():
            if k in node_name:
                lookup_key = k
                break
                
        # Clear existing rows
        self.info_table.setRowCount(0)
            
        if lookup_key:
            # Copy so the live status override below never mutates
            # sim_data itself - the fabricated placeholder fields
            # (Firmware, Frames RX/TX, Temperature, ...) stay as they
            # were for next time, only the exact top-level "Status" key
            # gets replaced with the real, live value from the node this
            # info table row set mirrors.
            data = dict(self.sim_data[lookup_key])
            node = next((n for n in self.canvas.nodes if n.key == lookup_key), None)
            if node is not None and "Status" in data:
                data["Status"] = node.status
            for k, val in data.items():
                row = self.info_table.rowCount()
                self.info_table.insertRow(row)
                self.info_table.setItem(row, 0, QTableWidgetItem(k))
                
                if "Status" in k:
                    lbl = StatusLabel(val)
                    self.info_table.setCellWidget(row, 1, lbl)
                else:
                    self.info_table.setItem(row, 1, QTableWidgetItem(val))
        else:
            # Generic/Future devices
            self.info_table.insertRow(0)
            self.info_table.setItem(0, 0, QTableWidgetItem(tr("pages.system_topology.fallback_property")))
            self.info_table.setItem(0, 1, QTableWidgetItem(tr("pages.system_topology.fallback_value")))
