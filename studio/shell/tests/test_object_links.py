"""Object step two (2026-09-18): one controller's tag read by another
controller of the same object, over the MQTT both already have. A link
in the object file becomes an incoming mapping in the target project's
mqtt.link_in (manual mappings untouched) and gives the source a topic
prefix and MQTT enabled; removing a controller drops its links."""
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QMessageBox

from studio.shell import main_window as mw
from studio.shell.main_window import StudioMainWindow
from studio.shell.project_format import Card, Location, MqttConfig, load_project, new_project, save_project
from studio.shell.project_panels import sync_points_for_card
from studio.shell.site_format import (apply_object_links, default_topic_prefix, drop_links_of, link_topic, load_site,
                                      new_site, save_site, suggest_link_tag)
from studio.shell.tests.test_controller_project_sync import _close


def _app():
    return QApplication.instance() or QApplication([])


def _site(tmp_path):
    site = new_site("Dom")
    site_path = tmp_path / "dom.epwsite"
    for name in ("EntryGate", "MainHouse"):
        folder = tmp_path / name
        folder.mkdir()
        project = new_project(name, author="t")
        project.locations = [Location("KOT", "Kotlownia")]
        card = Card("ELA1", "ELA", channel_kinds={"DI": 2, "AI": 1}, location="KOT")
        project.cards.append(card)
        sync_points_for_card(project, card)
        if name == "MainHouse":
            project.mqtt = MqttConfig(enabled=True, host="broker.lan", topic_prefix="epw/house",
                                      link_in=[{"topic": "manual/topic", "tag": "Link.HA.In1", "type": "BOOL",
                                                "stale_after_s": 30}])
        save_project(project, folder / "projekt.epw")
        site.projects.append(f"{name}/projekt.epw")
    save_site(site, site_path)
    return site_path


def test_the_pure_rules_topic_prefix_link_tag_and_apply():
    gate = new_project("Entry Gate", author="t")
    house = new_project("MainHouse", author="t")
    house.mqtt.link_in = [{"topic": "manual/topic", "tag": "Link.HA.In1", "type": "BOOL", "stale_after_s": 30}]
    assert default_topic_prefix(gate) == "epw/Entry_Gate"
    assert link_topic("epw/gate/", "ELA1.DI.1") == "epw/gate/tag/ELA1/DI/1/state"
    assert suggest_link_tag("Entry Gate", ["Link.Entry_Gate.In1"]) == "Link.Entry_Gate.In2"
    site = new_site("Dom")
    site.links = [{"source": "g", "tag": "ELA1.DI.1", "target": "h", "link_tag": "Link.EntryGate.In1", "type": "BOOL",
                   "stale_after_s": 20}]
    changed = apply_object_links(site, {"g": gate, "h": house})
    assert changed == {"g": ["topic_prefix=epw/Entry_Gate", "mqtt enabled"], "h": ["mqtt enabled", "1 object link(s)"]}
    assert gate.mqtt.enabled and gate.mqtt.topic_prefix == "epw/Entry_Gate" and gate.is_dirty
    assert house.mqtt.link_in == [
        {"topic": "manual/topic", "tag": "Link.HA.In1", "type": "BOOL", "stale_after_s": 30},
        {"topic": "epw/Entry_Gate/tag/ELA1/DI/1/state", "tag": "Link.EntryGate.In1", "type": "BOOL",
         "stale_after_s": 20, "object_link": True, "source": "g", "source_tag": "ELA1.DI.1"}]
    assert apply_object_links(site, {"g": gate, "h": house}) == {}          # idempotent
    assert drop_links_of(site, "g") == 1 and site.links == [] and site.is_dirty
    assert apply_object_links(site, {"g": gate, "h": house}) == {"h": ["0 object link(s)"]}
    assert house.mqtt.link_in[0]["tag"] == "Link.HA.In1" and len(house.mqtt.link_in) == 1


def test_a_link_added_in_studio_lands_in_the_target_project_and_survives_a_save(tmp_path, monkeypatch):
    _app()
    site_path = _site(tmp_path)
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat)
    win = StudioMainWindow(settings=settings)
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: QMessageBox.StandardButton.Ok)
    try:
        assert win._load_site_from_path(str(site_path))
        win._activate_slot(1)                                              # MainHouse is the active target
        win._open_object_links()
        panel = win._object_links_panel
        assert panel.add_button.isEnabled() and panel.rows() == []
        assert panel.create_link("EntryGate/projekt.epw", "ELA1.DI.1", "MainHouse/projekt.epw", "Link.EntryGate.In1", 45)
        assert panel.rows() == [("EntryGate", "ELA1.DI.1", "MainHouse", "Link.EntryGate.In1", "BOOL", 45)]

        house = win._project
        managed = [e for e in house.mqtt.link_in if e.get("object_link")]
        assert managed == [{"topic": "epw/EntryGate/tag/ELA1/DI/1/state", "tag": "Link.EntryGate.In1", "type": "BOOL",
                            "stale_after_s": 45, "object_link": True, "source": "EntryGate/projekt.epw",
                            "source_tag": "ELA1.DI.1"}]
        assert house.mqtt.link_in[0]["tag"] == "Link.HA.In1"               # the manual mapping stays first
        assert mw._TREE_ITEM_MQTT in win.edited_aspects()
        gate = win._slots[0].project
        assert gate.mqtt.enabled and gate.mqtt.topic_prefix == "epw/EntryGate" and gate.is_dirty
        assert win.device_names() == [("EntryGate", True), ("MainHouse", True)]

        assert not panel.create_link("EntryGate/projekt.epw", "ELA1.DI.2", "MainHouse/projekt.epw", "Link.EntryGate.In1")
        assert not panel.create_link("MainHouse/projekt.epw", "ELA1.DI.2", "MainHouse/projekt.epw", "Link.X.In9")
        assert not panel.create_link("EntryGate/projekt.epw", "ELA1.AI.1", "MainHouse/projekt.epw", "Bad.Tag")
        assert panel.create_link("EntryGate/projekt.epw", "ELA1.AI.1", "MainHouse/projekt.epw", "Link.EntryGate.In2")
        assert panel.rows()[1][4] == "REAL"

        win._open_mqtt()
        rows = win._mqtt_panel.links_table
        assert rows.rowCount() == 3 and not (rows.item(1, 0).flags() & rows.item(1, 0).flags().ItemIsEditable)
        win._mqtt_panel.links_table.setCurrentCell(1, 0)
        shown = []
        monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: shown.append(a[2]))
        win._mqtt_panel.remove_selected_link()
        assert shown and len(win._project.mqtt.link_in) == 3           # an object link is not removed there

        assert win._save_site()
        saved_site = load_site(site_path)
        assert [l["link_tag"] for l in saved_site.links] == ["Link.EntryGate.In1", "Link.EntryGate.In2"]
        assert load_project(tmp_path / "EntryGate" / "projekt.epw").mqtt.topic_prefix == "epw/EntryGate"
        assert [e["tag"] for e in load_project(tmp_path / "MainHouse" / "projekt.epw").mqtt.link_in] == \
            ["Link.HA.In1", "Link.EntryGate.In1", "Link.EntryGate.In2"]

        panel.table.selectRow(0)
        panel.table.setCurrentCell(0, 0)
        panel.remove_selected_link()
        assert [e["tag"] for e in win._project.mqtt.link_in] == ["Link.HA.In1", "Link.EntryGate.In2"]

        win._activate_slot(0)
        monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
        win._remove_device()                                              # EntryGate leaves: its link goes too
        assert win._site.links == [] and win._project.metadata.name == "MainHouse"
        assert [e["tag"] for e in win._project.mqtt.link_in] == ["Link.HA.In1"]
    finally:
        _close(win)


def test_without_a_second_controller_links_are_not_offered(tmp_path):
    _app()
    path = tmp_path / "solo" / "projekt.epw"
    path.parent.mkdir()
    save_project(new_project("Solo", author="t"), path)
    win = StudioMainWindow(settings=QSettings(str(tmp_path / "s.ini"), QSettings.IniFormat))
    try:
        win._load_project_from_path(str(path))
        win._open_object_links()
        assert not win._object_links_panel.add_button.isEnabled()
        assert win.object_devices() == [] and win.apply_object_links() == {}
    finally:
        _close(win)
