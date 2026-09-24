"""Renders the short animations the help shows next to a block
(logic_studio/help/media/<type_id>.gif) - owner 2026-09-25: "przy bramkach
logicznych przykłady zastosowania, może jakieś krótkie gify z działaniem".

Nothing here is drawn by hand: every frame is the editor's OWN canvas
(LogicScene, BlockItem, WireItem - the same code the engineer looks at)
showing a small diagram while the editor's OWN engine scans it, with the
inputs driven through the IOProvider exactly as the simulation panel
drives them. The GIF is written by gif_writer.py (plain Python, no new
dependency). Re-run after changing a block's look or semantics:

    python studio/logic/tools/render_help_animations.py          # all
    python studio/logic/tools/render_help_animations.py logic.and

Needs a display that renders text (on the developer's Windows PC: the
default QPA, not offscreen - offscreen draws text as boxes here).
"""
import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "studio" / "logic"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("EPW_TESTING", "1")

from PySide6.QtCore import QRectF, QSettings  # noqa: E402
from PySide6.QtGui import QImage, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from gif_writer import write_gif  # noqa: E402

MEDIA_DIR = REPO / "studio" / "logic" / "logic_studio" / "help" / "media"
SCALE = 1.25            # canvas px -> gif px
MARGIN = 18             # canvas px around the diagram
FRAME_MS = 700          # how long one input combination stays on screen
STEP_MS = 100           # the simulated scan period (timer frames advance by it)

DI = "input.di"
DO = "output.do"


class Diagram:
    """A small diagram on the editor's real canvas, scanned by its real engine."""

    def __init__(self):
        from logic_studio import i18n
        from logic_studio.core.device_model import DeviceModel
        from logic_studio.ui.main_window import MainWindow
        from shared.logic.engine.time_provider import SimulationTimeProvider
        i18n.set_language("pl")
        self._tmp = tempfile.mkdtemp()
        self.window = MainWindow(settings=QSettings(os.path.join(self._tmp, "s.ini"), QSettings.IniFormat))
        self.scene, self.project = self.window.scene, self.window.project
        self.scene.clear()
        DeviceModel.set_ela_devices(self.project, ["ELA01"])
        DeviceModel.set_ada_devices(self.project, ["ADA01"])
        self.items = []
        self.inputs = {}        # label -> address
        self.time = SimulationTimeProvider()
        self._n_di = 0
        self._n_do = 0

    def block(self, type_id, x, y, **props):
        from logic_studio.ui.canvas.block_item import BlockItem
        self.scene.add_block_from_library(type_id, x, y)
        block = self.project.blocks[-1]
        for key, value in props.items():
            block.properties[key] = value
        item = next(i for i in self.scene.items() if isinstance(i, BlockItem) and i.logic_block is block)
        self.items.append(item)
        return block

    def di(self, label, x, y):
        self._n_di += 1
        address = f"ELA01.DI.{self._n_di}"
        self.inputs[label] = address
        return self.block(DI, x, y, Address=address, Comment=label)

    def do(self, label, x, y):
        self._n_do += 1
        return self.block(DO, x, y, Address=f"ADA01.DO.{self._n_do}", Comment=label)

    def wire(self, src, out_idx, dst, in_idx):
        from logic_studio.core.wire import Wire
        assert src.outputs[out_idx].connect(dst.inputs[in_idx]), f"{src.type_id} -> {dst.type_id} refused"
        w = Wire()
        w.source_pin = src.outputs[out_idx].uuid
        w.dest_pin = dst.inputs[in_idx].uuid
        assert self.project.add_wire(w)

    def compile(self):
        self.scene._create_wire_items(self.items)
        self.window.compile_project()
        program = self.window.engine.program
        if not program or not program.execution_order:
            from logic_studio.compiler.core import Compiler
            comp = Compiler(self.project)
            comp.compile()
            raise RuntimeError(f"compile failed: {comp.errors}")
        self.window.engine.time = self.time
        self.window.engine.start()
        self.rect = self.scene.itemsBoundingRect().adjusted(-MARGIN, -MARGIN, MARGIN, MARGIN)

    def set_inputs(self, **values):
        for label, value in values.items():
            self.window.io_provider.set_digital_input(self.inputs[label], bool(value))

    def scan(self, n=1):
        """n scans of the real engine, the canvas mirrored after each -
        the same mirroring MainWindow._run_scan() does."""
        for _ in range(n):
            self.time.advance(STEP_MS)
            self.window.engine.step()
        self.window._mirror_engine_to_canvas()
        self.scene.refresh_live_states()
        self.scene.update()
        QApplication.instance().processEvents()

    def frame(self) -> QImage:
        width, height = int(self.rect.width() * SCALE), int(self.rect.height() * SCALE)
        image = QImage(width, height, QImage.Format.Format_RGB32)
        image.fill(0xFFFFFFFF)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        self.scene.render(painter, QRectF(0, 0, width, height), self.rect)
        painter.end()
        return image

    def close(self):
        self.window.engine.stop()
        self.window.is_dirty = False
        self.window.close()


# --- scenarios -------------------------------------------------------------------------------------
# Each returns (diagram, steps): steps = [(inputs dict, scans, hold_ms)].

def _two_input_gate(type_id):
    d = Diagram()
    a = d.di("A", 40, 40)
    b = d.di("B", 40, 130)
    g = d.block(type_id, 240, 75)
    q = d.do("Q", 380, 75)
    d.wire(a, 0, g, 0)
    d.wire(b, 0, g, 1)
    d.wire(g, 0, q, 0)
    d.compile()
    steps = [({"A": 0, "B": 0}, 2, FRAME_MS), ({"A": 1, "B": 0}, 2, FRAME_MS),
             ({"A": 1, "B": 1}, 2, FRAME_MS), ({"A": 0, "B": 1}, 2, FRAME_MS)]
    return d, steps


def _one_input_gate(type_id):
    d = Diagram()
    a = d.di("A", 40, 40)
    g = d.block(type_id, 240, 40)
    q = d.do("Q", 380, 40)
    d.wire(a, 0, g, 0)
    d.wire(g, 0, q, 0)
    d.compile()
    steps = [({"A": 0}, 2, FRAME_MS), ({"A": 1}, 2, FRAME_MS)]
    return d, steps


def _latch(type_id):
    d = Diagram()
    s = d.di("S", 40, 40)
    r = d.di("R", 40, 130)
    m = d.block(type_id, 240, 75)
    q = d.do("Q", 400, 75)
    # SR: S1 first, R second; RS: R1 first, S second
    if type_id == "memory.sr":
        d.wire(s, 0, m, 0)
        d.wire(r, 0, m, 1)
    else:
        d.wire(r, 0, m, 0)
        d.wire(s, 0, m, 1)
    d.wire(m, 0, q, 0)
    d.compile()
    steps = [({"S": 0, "R": 0}, 2, FRAME_MS), ({"S": 1, "R": 0}, 2, FRAME_MS), ({"S": 0, "R": 0}, 2, FRAME_MS),
             ({"S": 0, "R": 1}, 2, FRAME_MS), ({"S": 0, "R": 0}, 2, FRAME_MS), ({"S": 1, "R": 1}, 2, FRAME_MS),
             ({"S": 0, "R": 0}, 2, FRAME_MS)]
    return d, steps


def _timer(type_id):
    d = Diagram()
    a = d.di("IN", 40, 40)
    t = d.block(type_id, 240, 40)
    t.properties["Preset (ms)"] = 500
    q = d.do("Q", 420, 40)
    d.wire(a, 0, t, 0)
    d.wire(t, 0, q, 0)
    d.compile()
    tick = 350
    if type_id == "timer.ton":
        steps = [({"IN": 0}, 1, FRAME_MS)] + [({"IN": 1}, 1, tick)] * 7 + [({"IN": 0}, 1, FRAME_MS)]
    elif type_id == "timer.tof":
        steps = [({"IN": 0}, 1, FRAME_MS), ({"IN": 1}, 1, FRAME_MS)] + [({"IN": 0}, 1, tick)] * 7
    else:  # TP: a short IN pulse, Q stays for PT
        steps = [({"IN": 0}, 1, FRAME_MS), ({"IN": 1}, 1, tick), ({"IN": 0}, 1, tick)] + [({"IN": 0}, 1, tick)] * 5
    return d, steps


def _edge(type_id):
    d = Diagram()
    a = d.di("IN", 40, 40)
    e = d.block(type_id, 240, 40)
    q = d.do("Q", 400, 40)
    d.wire(a, 0, e, 0)
    d.wire(e, 0, q, 0)
    d.compile()
    steps = [({"IN": 0}, 1, FRAME_MS), ({"IN": 1}, 1, 450), ({"IN": 1}, 1, FRAME_MS),
             ({"IN": 0}, 1, 450), ({"IN": 0}, 1, FRAME_MS)]
    return d, steps


def _counter(type_id):
    d = Diagram()
    cu = d.di("CU", 40, 40)
    r = d.di("R", 40, 130)
    c = d.block(type_id, 240, 60)
    c.properties["Preset"] = 3
    q = d.do("Q", 420, 60)
    d.wire(cu, 0, c, 0)
    d.wire(r, 0, c, 1)
    d.wire(c, 0, q, 0)
    d.compile()
    steps = [({"CU": 0, "R": 0}, 1, FRAME_MS)]
    for _ in range(3):
        steps += [({"CU": 1, "R": 0}, 1, 450), ({"CU": 0, "R": 0}, 1, 450)]
    steps += [({"CU": 0, "R": 1}, 1, FRAME_MS), ({"CU": 0, "R": 0}, 1, FRAME_MS)]
    return d, steps


SCENARIOS = {
    "logic.and": lambda: _two_input_gate("logic.and"),
    "logic.or": lambda: _two_input_gate("logic.or"),
    "logic.nand": lambda: _two_input_gate("logic.nand"),
    "logic.nor": lambda: _two_input_gate("logic.nor"),
    "logic.xor": lambda: _two_input_gate("logic.xor"),
    "logic.xnor": lambda: _two_input_gate("logic.xnor"),
    "logic.not": lambda: _one_input_gate("logic.not"),
    "logic.buffer": lambda: _one_input_gate("logic.buffer"),
    "memory.sr": lambda: _latch("memory.sr"),
    "memory.rs": lambda: _latch("memory.rs"),
    "timer.ton": lambda: _timer("timer.ton"),
    "timer.tof": lambda: _timer("timer.tof"),
    "timer.tp": lambda: _timer("timer.tp"),
    "edge.rtrig": lambda: _edge("edge.rtrig"),
    "edge.ftrig": lambda: _edge("edge.ftrig"),
    "edge.change": lambda: _edge("edge.change"),
    "counter.ctu": lambda: _counter("counter.ctu"),
}


# --- frames -> gif ---------------------------------------------------------------------------------

def _quantize(frames):
    """One palette for every frame (Qt's own Indexed8 conversion on the
    frames stacked together), then each frame's indices against it."""
    width, height = frames[0].width(), frames[0].height()
    stack = QImage(width, height * len(frames), QImage.Format.Format_RGB32)
    painter = QPainter(stack)
    for n, frame in enumerate(frames):
        painter.drawImage(0, n * height, frame)
    painter.end()
    indexed = stack.convertToFormat(QImage.Format.Format_Indexed8)
    table = indexed.colorTable()
    palette = [((c >> 16) & 0xFF, (c >> 8) & 0xFF, c & 0xFF) for c in table]
    out = []
    stride = indexed.bytesPerLine()
    raw = bytes(indexed.constBits())
    for n in range(len(frames)):
        rows = []
        for y in range(n * height, (n + 1) * height):
            rows.append(raw[y * stride: y * stride + width])
        out.append(b"".join(rows))
    return width, height, palette, out


def render(type_id: str, out_dir: Path = MEDIA_DIR) -> Path:
    diagram, steps = SCENARIOS[type_id]()
    try:
        frames, delays = [], []
        for inputs, scans, hold in steps:
            diagram.set_inputs(**inputs)
            diagram.scan(scans)
            frames.append(diagram.frame())
            delays.append(hold)
    finally:
        diagram.close()
    width, height, palette, indices = _quantize(frames)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{type_id}.gif"
    write_gif(str(path), width, height, palette, indices, delays)
    return path


def main(argv):
    app = QApplication.instance() or QApplication([])
    from shared.logic.blocks import register_builtin_blocks
    register_builtin_blocks()
    wanted = argv or list(SCENARIOS)
    for type_id in wanted:
        path = render(type_id)
        print(f"{type_id}: {path.name} ({path.stat().st_size} B)")
    return app


if __name__ == "__main__":
    main(sys.argv[1:])
