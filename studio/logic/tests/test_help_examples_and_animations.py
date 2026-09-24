"""Owner 2026-09-25: "więcej w dziale pomoc, bardziej szczegółowo; przy
bramkach logicznych przykłady zastosowania, może jakieś krótkie gify z
działaniem". The generated block pages of gates, latches, timers, edges
and counters carry hand-written examples in both languages and an
animation rendered from the editor's own canvas; the help viewer plays
it; the canvas mirrors the engine's values during a simulation (which is
what the animations show, and what the guide promises)."""
import os
import re
import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtGui import QMovie, QTextDocument
from PySide6.QtWidgets import QApplication

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_REPO_ROOT = Path(__file__).resolve().parents[3]
for p in (str(_REPO_ROOT), str(_REPO_ROOT / "studio" / "logic" / "tools")):
    if p not in sys.path:
        sys.path.insert(0, p)

from logic_studio import i18n  # noqa: E402
from logic_studio.core import block_catalog  # noqa: E402
from logic_studio.core.help_content import (HELP_ROOT, MEDIA_ROOT, BLOCK_EXAMPLES_DIR, HelpContentStore,  # noqa: E402
                                            animation_path, animation_url)
from shared.help_animation import AnimatedHelpBrowser  # noqa: E402
from shared.logic.blocks import register_builtin_blocks  # noqa: E402
from shared.logic.blocks.registry import BlockRegistry  # noqa: E402

register_builtin_blocks()

EXAMPLE_CATEGORIES = ("Logic gates", "Flip-flops", "Timers", "Edge detection", "Counters")
_LINK_RE = re.compile(r"\]\(help:([^)\s]+)\)")


@pytest.fixture(autouse=True)
def _restore_language():
    before = i18n.get_language()
    yield
    i18n.set_language(before)


def _app():
    return QApplication.instance() or QApplication([])


def _example_ids(language):
    return sorted(p.stem for p in (Path(HELP_ROOT) / language / BLOCK_EXAMPLES_DIR).glob("*.md"))


def _types_in(categories):
    return sorted(t for c in categories for t in BlockRegistry.get_blocks_in_category(c))


# --- the example files -------------------------------------------------------------------------------

@pytest.mark.parametrize("language", ["pl", "en"])
def test_every_example_file_names_a_registered_block_type(language):
    known = set(block_catalog.all_type_ids())
    ids = _example_ids(language)
    assert ids, "no example files"
    for type_id in ids:
        assert type_id in known, f"{language}/blocks/{type_id}.md is not a registered block type"


def test_every_gate_latch_timer_edge_and_counter_has_examples_in_both_languages():
    expected = _types_in(EXAMPLE_CATEGORIES)
    assert len(expected) >= 25
    assert _example_ids("pl") == expected
    assert _example_ids("en") == expected


@pytest.mark.parametrize("language", ["pl", "en"])
def test_example_links_resolve_and_the_text_is_substantive(language):
    store = HelpContentStore(language)
    known = {topic_id for topic_id, _t, _c in store.all_topics()} | {"shortcuts"}
    for type_id in _example_ids(language):
        text = (Path(HELP_ROOT) / language / BLOCK_EXAMPLES_DIR / f"{type_id}.md").read_text(encoding="utf-8")
        assert len(text) > 250, f"{language}/{type_id}: too thin to be an example"
        assert "###" in text, f"{language}/{type_id}: no example headings"
        for target in _LINK_RE.findall(text):
            assert target in known, f"{language}/blocks/{type_id}.md links to help:{target}, unknown"


def test_the_two_input_gates_carry_a_truth_table_in_both_languages():
    for language, header in (("pl", "Tabela prawdy"), ("en", "Truth table")):
        for gate in ("logic.and", "logic.or", "logic.nand", "logic.nor", "logic.xor", "logic.xnor", "logic.not"):
            text = (Path(HELP_ROOT) / language / BLOCK_EXAMPLES_DIR / f"{gate}.md").read_text(encoding="utf-8")
            assert header in text and "| In1 |" in text, (language, gate)


# --- the animations ----------------------------------------------------------------------------------

def test_every_animation_names_a_registered_type_and_every_scenario_was_rendered():
    from render_help_animations import SCENARIOS
    known = set(block_catalog.all_type_ids())
    rendered = sorted(p.stem for p in Path(MEDIA_ROOT).glob("*.gif"))
    assert rendered, "no animations - run studio/logic/tools/render_help_animations.py"
    for type_id in rendered:
        assert type_id in known, f"media/{type_id}.gif is not a registered block type"
    assert rendered == sorted(SCENARIOS), "re-run render_help_animations.py: scenarios and files differ"
    for gate in ("logic.and", "logic.or", "logic.not", "logic.xor", "memory.sr", "timer.ton", "edge.rtrig"):
        assert animation_path(gate) and animation_url(gate).startswith("file:///")
    assert animation_path("math.add") is None


def test_every_animation_decodes_with_more_than_one_frame():
    _app()
    for path in sorted(Path(MEDIA_ROOT).glob("*.gif")):
        movie = QMovie(str(path))
        movie.setCacheMode(QMovie.CacheMode.CacheAll)
        assert movie.isValid(), path.name
        assert movie.jumpToFrame(0)
        assert movie.frameCount() >= 2, path.name
        image = movie.currentImage()
        assert image.width() > 300 and image.height() > 100, path.name


def test_the_gif_writer_round_trips_through_qmovie(tmp_path):
    from gif_writer import write_gif
    _app()
    palette = [(255, 255, 255), (0, 170, 0), (0, 0, 0)]
    width, height = 6, 4
    frame_a = bytes([0] * (width * height))
    frame_b = bytes([1] * (width * height))
    frame_c = bytes([2] * (width * height))
    path = tmp_path / "t.gif"
    write_gif(str(path), width, height, palette, [frame_a, frame_b, frame_c], [700, 350, 1000])
    movie = QMovie(str(path))
    movie.setCacheMode(QMovie.CacheMode.CacheAll)
    assert movie.isValid() and movie.jumpToFrame(0) and movie.frameCount() == 3
    colours = []
    for i in range(3):
        movie.jumpToFrame(i)
        image = movie.currentImage()
        assert (image.width(), image.height()) == (width, height)
        colours.append(image.pixelColor(2, 2).name())
    assert colours == ["#ffffff", "#00aa00", "#000000"]
    with pytest.raises(ValueError):
        write_gif(str(path), width, height, palette, [frame_a], [700, 700])


# --- the generated page --------------------------------------------------------------------------------

def test_a_gates_page_carries_the_animation_and_the_examples_in_the_interface_language():
    i18n.set_language("pl")
    page = HelpContentStore("pl").load_topic_markdown("block:logic.and")
    assert page.startswith("# ")
    assert "![Animacja działania bloku](file:///" in page and page.index("![Animacja") < page.index("## Piny")
    assert "*Animacja: schemat z edytora w symulacji" in page
    assert "## Przykłady zastosowania" in page and "Tabela prawdy" in page
    assert page.index("## Przykłady zastosowania") > page.index("## Piny")
    i18n.set_language("en")
    page = HelpContentStore("en").load_topic_markdown("block:logic.and")
    assert "![Animation of the block at work](file:///" in page and "## Examples of use" in page
    assert "Truth table" in page and "Przykłady" not in page


def test_a_block_without_extras_keeps_its_plain_catalogue_page():
    i18n.set_language("pl")
    page = HelpContentStore("pl").load_topic_markdown("block:math.add")
    assert "## Przykłady zastosowania" not in page and "![" not in page and "## Piny" in page


def test_a_language_without_examples_falls_back_to_polish():
    store = HelpContentStore("de")
    assert "Tabela prawdy" in store.block_examples_markdown("logic.and")
    assert store.block_examples_markdown("math.add") == ""


def test_search_finds_a_block_by_the_words_of_its_examples():
    i18n.set_language("pl")
    hits = dict(HelpContentStore("pl").search("wybieg wentylatora"))
    assert "block:timer.tof" in hits and "guide_typical_circuits" in hits


# --- the viewer plays it ---------------------------------------------------------------------------------

def test_the_help_browser_plays_a_gif_and_stops_it_on_the_next_page():
    app = _app()
    browser = AnimatedHelpBrowser()
    url = animation_url("logic.and")
    browser.setMarkdown(f"# AND\n\n![Animacja](({url}))\n\n![Animacja]({url})\n\ntekst")
    browser.show()
    for _ in range(20):
        app.processEvents()
    assert browser.animations() == [url]
    resource = browser.document().resource(QTextDocument.ResourceType.ImageResource, QUrl(url))
    assert resource is not None and not resource.isNull()
    assert resource.width() > 300, "the frame the document draws is the rendered canvas, not a placeholder"
    browser.setMarkdown("# Inna strona\n\nbez animacji")
    assert browser.animations() == []
    browser.close()


def test_the_logic_help_window_shows_the_animation_on_a_gate_page(qsettings):
    from logic_studio.ui.help_window import HelpWindow
    app = _app()
    win = HelpWindow(settings=qsettings)
    assert isinstance(win.viewer, AnimatedHelpBrowser)
    win.show()                      # the document asks for its images once it is laid out on screen
    win.navigate_to("block:logic.and")
    for _ in range(20):
        app.processEvents()
    assert win.viewer.animations() == [animation_url("logic.and")]
    win.navigate_to("concept_gates")
    assert win.viewer.animations() == []
    assert "Bramki logiczne" in win.viewer.toPlainText() or "Logic gates" in win.viewer.toPlainText()
    win.close()


# --- the canvas shows what the engine computed --------------------------------------------------------

def test_a_simulation_scan_mirrors_the_engines_values_onto_the_canvas(qsettings):
    from logic_studio.core.device_model import DeviceModel
    from logic_studio.ui.canvas import style
    from logic_studio.ui.canvas.wire_item import WireItem
    from logic_studio.ui.main_window import MainWindow
    _app()
    window = MainWindow(settings=qsettings)
    try:
        DeviceModel.set_ela_devices(window.project, ["ELA01"])
        DeviceModel.set_ada_devices(window.project, ["ADA01"])
        window.scene.clear()
        window.scene.add_block_from_library("input.di", 0, 0)
        window.scene.add_block_from_library("logic.not", 120, 0)
        window.scene.add_block_from_library("output.do", 240, 0)
        di, no, do = window.project.blocks[:3]
        di.update_property("Address", "ELA01.DI.1")
        do.update_property("Address", "ADA01.DO.1")
        di.outputs[0].connect(no.inputs[0])
        no.outputs[0].connect(do.inputs[0])
        from logic_studio.ui.canvas.block_item import BlockItem
        window.scene._create_wire_items([i for i in window.scene.items() if isinstance(i, BlockItem)])
        window.compile_project()
        window.engine.start()
        window.io_provider.set_digital_input("ELA01.DI.1", False)
        window.engine.step()
        window._mirror_engine_to_canvas()
        window.scene.refresh_live_states()
        assert di.outputs[0].value is False and no.outputs[0].value is True and do.inputs[0].value is True
        assert di.simulation_state.get("sim_value") is False
        wires = {w.source_port.pin.uuid: w for w in window.scene.items() if isinstance(w, WireItem)}
        assert wires[no.outputs[0].uuid].color == style.COLOR_LOGIC_HIGH
        assert wires[di.outputs[0].uuid].color == style.COLOR_LOGIC_LOW
        # and the ordinary scan does the same on its own
        window.io_provider.set_digital_input("ELA01.DI.1", True)
        window._run_scan()
        window.io_provider.set_digital_input("ELA01.DI.1", True)      # _run_scan pushes the panel's own inputs
        window.engine.step()
        window._mirror_engine_to_canvas()
        window.scene.refresh_live_states()
        assert no.outputs[0].value is False
        assert wires[no.outputs[0].uuid].color == style.COLOR_LOGIC_LOW
        window.stop_simulation()
        assert di.outputs[0].value is None
    finally:
        window.is_dirty = False
        window.close()
