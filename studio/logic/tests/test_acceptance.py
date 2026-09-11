import pytest
from PySide6.QtWidgets import QApplication
from logic_studio.ui.main_window import MainWindow
from logic_studio.blocks import register_builtin_blocks

import os
import json
from pathlib import Path

# fix/logic-tests-regression: was os.path.abspath("examples/...") in each
# test below, resolved against the process's CWD. That only ever worked
# because CWD happened to be this package's own root (studio/logic/) -
# true when Logic Studio was its own standalone repo, silently false
# after the monorepo merge (c250b02) moved studio/logic one level down.
# Anchored to this file's own location instead - see this branch's own
# report for the full bisection.
EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"
LOGIC_STUDIO_DIR = Path(__file__).resolve().parent.parent

def test_file_operations_and_export(qsettings, tmp_path):
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    register_builtin_blocks()
    m = MainWindow(settings=qsettings)

    # Simulate loading the examples project
    test_proj = str(EXAMPLES_DIR / "ENTRY_GATE_MINIMAL.epwlogic")
    assert os.path.exists(test_proj)

    # We bypass QFileDialog for automation
    m.stop_simulation()
    m.scene.clear()
    from logic_studio.core.project import Project
    m.project = Project.load_from_file(test_proj)
    m.engine.project = m.project
    m.current_file = test_proj
    m._reconstruct_scene()

    assert len(m.project.blocks) == 3
    assert len(m.scene.items()) > 0

    # Validate compile and runtime export bypass
    m.compile_project()
    assert len(m.engine.program.execution_order) == 3

    from logic_studio.compiler.exporter import Exporter
    exporter = Exporter(m.project, m.engine.program.execution_order)
    runtime_data = exporter.export()

    assert "format" in runtime_data
    assert len(runtime_data["blocks"]) == 3

    # Save as temp file to verify - pytest's own tmp_path (not a bare
    # relative name resolved against CWD, and not this test's own
    # responsibility to clean up: pytest removes tmp_path for us,
    # whether the test passes or fails).
    temp_path = str(tmp_path / "temp_test.epwlogic")
    m.project.save_to_file(temp_path)
    assert os.path.exists(temp_path)

def test_final_acceptance_project(qsettings):
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    register_builtin_blocks()
    m = MainWindow(settings=qsettings)

    test_proj = str(EXAMPLES_DIR / "EPW_LOGIC_FINAL_UI_TEST.epwlogic")
    assert os.path.exists(test_proj)

    m.stop_simulation()
    m.scene.clear()
    from logic_studio.core.project import Project
    m.project = Project.load_from_file(test_proj)
    m.engine.project = m.project
    m.current_file = test_proj
    m._reconstruct_scene()

    # 2 docs + 2 DI + 1 AND + 1 DO = 6 blocks
    assert len(m.project.blocks) == 6

    m.compile_project()
    # Exclude docs from execution order
    assert len(m.engine.program.execution_order) == 4

    # Check if simulation handles execution order properly
    m.start_simulation()
    m.engine.step()
    m.stop_simulation()

def test_headless_engine_no_qt():
    import sys
    import subprocess
    import tempfile

    # Run a python process that imports ExecutionEngine and blocks,
    # and asserts that 'PySide6' is not in sys.modules.
    script = """
import sys
from logic_studio.engine.execution import ExecutionEngine
from logic_studio.compiler.core import Compiler
from logic_studio.core.project import Project
from logic_studio.blocks.logic_gates import AndGate

assert 'PySide6' not in sys.modules, "PySide6 was imported!"
assert 'logic_studio.ui' not in sys.modules, "UI package was imported!"
"""

    # fix/logic-tests-regression: was open('test_headless_import.py', 'w')
    # (a bare relative name, written to whatever the process's CWD
    # happened to be) plus an os.remove() AFTER the assert - so a failing
    # subprocess (as it always did once CWD stopped being studio/logic/,
    # see below) left the scratch script behind instead of cleaning it up.
    # That is the exact origin of the untracked test_headless_import.py
    # this branch's own report found sitting at the repo root.
    #
    # Two independent things had to be fixed, not just relocated:
    #  1. `from logic_studio...` inside the SUBPROCESS's own script only
    #     resolves when studio/logic/ is on ITS sys.path - true when the
    #     script file itself lives in studio/logic/ (a bare `python
    #     script.py` puts the script's own directory at sys.path[0]).
    #     Writing the scratch script into studio/logic/ instead of
    #     wherever the OUTER test's CWD is achieves that regardless of
    #     how pytest itself was invoked.
    #  2. Cleanup must run even when the assert below fails - a bare
    #     "next line" statement never does that; try/finally does.
    fd, script_path = tempfile.mkstemp(suffix=".py", dir=str(LOGIC_STUDIO_DIR))
    try:
        with os.fdopen(fd, "w") as f:
            f.write(script)
        res = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
        assert res.returncode == 0, f"Headless import test failed: {res.stderr}"
    finally:
        os.remove(script_path)
