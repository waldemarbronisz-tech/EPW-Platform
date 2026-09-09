from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtCore import Qt, QTimer, Signal, QRect
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFontMetrics
import time

class TopologyNode:
    def __init__(self, key, name, description, x, y, is_master=False):
        self.key = key
        self.name = name
        self.description = description
        self.x = x
        self.y = y
        self.width = 140
        self.height = 70
        self.is_master = is_master
        
        # Seeded OFFLINE, not a hopeful "ONLINE" default - same
        # conservative convention as the Device.*.Status tags in
        # tag_manager.py's init_default_tags(). PageSystemTopology
        # overwrites this with the real value immediately on construction
        # (_seed_device_statuses()); this default only matters if that
        # ever doesn't run.
        self.status = "OFFLINE"
        self.selected = False
        
        self.rx_active = False
        self.tx_active = False
        self.rx_timer = 0
        self.tx_timer = 0
        
    def trigger_rx(self):
        self.rx_active = True
        self.rx_timer = time.time()
        
    def trigger_tx(self):
        self.tx_active = True
        self.tx_timer = time.time()
        
    def get_rect(self):
        return QRect(self.x, self.y, self.width, self.height)

class TopologyCanvas(QWidget):
    node_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SunkenFrame")
        # Grows to fill the splitter pane; the diagram lays itself out
        # against the live width AND height in paintEvent.
        self.setMinimumSize(360, 320)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.nodes = []
        self.bus_y = 150  # recomputed from the widget height on every paint

        self.setup_nodes()
        
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.simulate_and_paint)
        self.anim_timer.start(50) # 60fps roughly
        
        self.anim_offset = 0
        self.anim_direction = 1

    def setup_nodes(self):
        # Initial positions. The paintEvent handles symmetrical distribution
        # Nodes will be updated dynamically but we store their base types
        self.nodes = [
            TopologyNode("EPW Controller", "EPW Controller", "Main Controller", 0, 40, is_master=True),
            TopologyNode("ELA-01", "ELA-01", "Digital Inputs", -200, 220),
            TopologyNode("ADA-01", "ADA-01", "Digital Outputs", 0, 220),
            TopologyNode("EPM-01", "EPM-01", "Power Measurement", 200, 220)
        ]
        
        # 20% smaller than before (140x70 -> approx 110x56)
        for n in self.nodes:
            n.width = 112
            n.height = 56
            
    def simulate_and_paint(self):
        # Decay LEDs
        current_time = time.time()
        needs_update = False
        
        self.anim_offset = (self.anim_offset + (2 * self.anim_direction)) % 20
        
        for n in self.nodes:
            if n.status == "ONLINE":
                if False:
                    n.trigger_rx()
                if False:
                    n.trigger_tx()
            
            if n.rx_active and (current_time - n.rx_timer > 0.2): # 200ms
                n.rx_active = False
            if n.tx_active and (current_time - n.tx_timer > 0.2):
                n.tx_active = False
                
        self.update()

    def mousePressEvent(self, event):
        pos = event.position().toPoint()
        
        center_x = self.width() // 2
        for n in self.nodes:
            # Reconstruct screen rect
            rx = center_x + n.x - (n.width // 2)
            rect = QRect(rx, n.y, n.width, n.height)
            if rect.contains(pos):
                for node in self.nodes:
                    node.selected = False
                n.selected = True
                self.node_selected.emit(n.key)
                self.update()
                return

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Dynamically scale placement based on actual window size
        w = self.width()
        h = self.height()
        center_x = w // 2

        # Override node positions for symmetrical distribution
        # EPW at top center
        epw_n = next(n for n in self.nodes if n.is_master)
        epw_n.x = 0

        # Distribute slaves evenly
        slaves = [n for n in self.nodes if not n.is_master]
        # ELA, ADA, EPM spread across the bus
        bus_width = int(w * 0.7)
        bus_start_x = center_x - (bus_width // 2)

        spacing = bus_width // (len(slaves) - 1) if len(slaves) > 1 else bus_width // 2
        for i, slv in enumerate(slaves):
            slv.x = (bus_start_x + i * spacing) - center_x

        # Vertical layout scaled to the current height too - previously
        # fixed (master y=40, bus_y=150, slaves y=220), so a tall window
        # (this canvas grows to fill it now that the main window is
        # resizable) left everything clustered in the top ~280px with a
        # big empty area below. A node body + RX/TX row needs ~80px clear.
        node_clearance = 80
        epw_n.y = max(20, int(h * 0.10))
        self.bus_y = max(epw_n.y + epw_n.height + 20, int(h * 0.42))
        slave_y = max(self.bus_y + 20, int(h * 0.68))
        slave_y = min(slave_y, h - node_clearance)
        for slv in slaves:
            slv.y = slave_y

        # Draw RS485 and SPI buses
        # We split the bus into two logical segments drawn together for alignment
        # Left half = RS485, Right half = SPI
        p.setPen(QPen(QColor("black"), 3))
        p.drawLine(bus_start_x, self.bus_y, center_x, self.bus_y) # RS485
        p.drawLine(center_x, self.bus_y, bus_start_x + bus_width, self.bus_y) # SPI
        
        fm = p.fontMetrics()
        p.drawText(center_x - 100, self.bus_y - 10, "RS485 BUS")
        p.drawText(center_x + 50, self.bus_y - 10, "SPI BUS")
        
        # Moving dots along backbone
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("green")))
        for i in range(self.anim_offset, bus_width, 20):
            p.drawEllipse(bus_start_x + i - 2, self.bus_y - 2, 4, 4)
            
        # Draw Branches
        p.setPen(QPen(QColor("black"), 2))
        for n in self.nodes:
            nx = center_x + n.x
            
            if n.is_master:
                # Draw down to bus
                p.drawLine(nx, n.y + n.height, nx, self.bus_y)
                # Moving dots vertical master
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(QColor("green")))
                dist = self.bus_y - (n.y + n.height)
                for i in range(self.anim_offset, dist, 20):
                    p.drawEllipse(nx - 2, n.y + n.height + i - 2, 4, 4)
                p.setPen(QPen(QColor("black"), 2))
            else:
                # Draw up to bus
                p.drawLine(nx, self.bus_y, nx, n.y)
                # Moving dots vertical slave
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(QColor("green")))
                dist = n.y - self.bus_y
                for i in range(self.anim_offset, dist, 20):
                    p.drawEllipse(nx - 2, self.bus_y + i - 2, 4, 4)
                p.setPen(QPen(QColor("black"), 2))

        # Draw Nodes
        for n in self.nodes:
            nx = center_x + n.x - (n.width // 2)
            ny = n.y
            
            # Node background
            p.setPen(QPen(QColor("blue" if n.selected else "black"), 2 if n.selected else 1))
            p.setBrush(QBrush(QColor("#D4D0C8")))
            p.drawRect(nx, ny, n.width, n.height)
            
            # Header
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor("#000080")))
            p.drawRect(nx, ny, n.width, 16)
            
            p.setPen(QPen(QColor("white")))
            tw = fm.horizontalAdvance(n.name)
            p.drawText(nx + (n.width - tw)//2, ny + 12, n.name)
            
            # Desc
            p.setPen(QPen(QColor("black")))
            tw = fm.horizontalAdvance(n.description)
            p.drawText(nx + (n.width - tw)//2, ny + 28, n.description)
            
            # Status - COMM_FAILURE added alongside the pre-existing cases
            # when node status was wired to the real Device.*.Status tags
            # (Task 1): it's a real DeviceManager/DeviceStatus value (see
            # device_manager.py), and StatusLabel (the widget the Main
            # View Device Status panel uses for the very same tags)
            # already colors anything containing "FAILURE" red - matching
            # that here keeps the two views visually consistent, not just
            # textually.
            stat_color = QColor("green")
            if n.status == "OFFLINE": stat_color = QColor("gray")
            elif n.status == "COMM_FAILURE": stat_color = QColor("red")
            elif n.status == "WARNING": stat_color = QColor("orange")
            elif n.status == "STARTING": stat_color = QColor("yellow")
            elif n.status == "FAULT": stat_color = QColor("red")
            
            tw = fm.horizontalAdvance(n.status)
            p.setPen(QPen(stat_color))
            # Mocking the StatusLabel style visually
            p.setBrush(QBrush(QColor("black")))
            stat_rect = QRect(nx + 5, ny + 32, n.width - 10, 15)
            p.drawRect(stat_rect)
            p.drawText(stat_rect, Qt.AlignmentFlag.AlignCenter, n.status)
            
            # RX / TX LEDs
            # Size 6x6 as requested, directly below status
            p.setPen(QPen(QColor("black"), 1))
            
            rx_color = QColor("#00FF00") if n.rx_active else QColor("gray")
            tx_color = QColor("#FFA500") if n.tx_active else QColor("gray")
            if n.status == "OFFLINE":
                rx_color = tx_color = QColor("gray")
            elif n.status == "COMM_FAILURE":
                rx_color = tx_color = QColor("red")
            elif n.status == "TIMEOUT":
                rx_color = tx_color = QColor("red")
                
            rx_x = nx + 25
            tx_x = nx + n.width - 25 - 6
            led_y = ny + 49
            
            p.setBrush(QBrush(rx_color))
            p.drawEllipse(rx_x, led_y, 6, 6)
            p.setPen(QPen(QColor("black")))
            p.drawText(rx_x - 14, led_y + 7, "RX")
            
            p.setBrush(QBrush(tx_color))
            p.drawEllipse(tx_x, led_y, 6, 6)
            p.setPen(QPen(QColor("black")))
            p.drawText(tx_x + 10, led_y + 7, "TX")
