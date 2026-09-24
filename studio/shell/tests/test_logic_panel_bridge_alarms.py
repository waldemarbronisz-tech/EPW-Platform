"""Signal register etap 5: Studio's process protections reach the embedded
Logic Studio the same way its zones do (LogicPanel.sync_cards_from_
studio), so the catalogue's ALM.<alarm_id>.* patterns become one signal
per protection in the picker and the validator."""
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from shared.logic import system_signals
from studio.shell.logic_panel import LogicPanel
from studio.shell.project_format import Card, Point, ProcessProtection, new_project


def _app():
    return QApplication.instance() or QApplication([])


def _panel(tmp_path):
    _app()
    return LogicPanel(settings=QSettings(str(tmp_path / "logic.ini"), QSettings.IniFormat))


def test_a_process_protection_becomes_its_own_alarm_signals_in_logic_studio(tmp_path):
    panel = _panel(tmp_path)
    studio_project = new_project("Test")
    studio_project.cards.append(Card(id="ELA1", model="ELA01", channel_kinds={"AI": 2}))
    studio_project.points.append(Point(address="ELA1.AI.1", description="Temperatura"))
    studio_project.process_protections.append(ProcessProtection(id="PP1", name="Temperatura kotla", analog_tag="ELA1.AI.1"))
    panel.sync_cards_from_studio(studio_project)

    logic_project = panel.main_window().project
    alarm_ids = [a["id"] for a in logic_project.external_alarms]
    assert alarm_ids[:4] == ["EMERGENCY_STOP", "SYSTEM_HEALTH", "REMOTE_COMMAND_REFUSED", "ALM_TEST"]
    assert "DEVICE_COMM_ELA1" in alarm_ids and "DEVICE_HEALTH_ELA1" in alarm_ids and "PROCESS_PP1" in alarm_ids
    assert "PROT_SETTINGS_MISMATCH_ELA1" not in alarm_ids, "only an ADA card carries protection settings"
    ids = {s["id"]: s for s in system_signals.get_all_signals(logic_project)}
    assert {"ALM.PROCESS_PP1.ACTIVE", "ALM.PROCESS_PP1.ACKNOWLEDGED", "ALM.PROCESS_PP1.LATCHED",
            "ALM.DEVICE_COMM_ELA1.ACTIVE", "ALM.EMERGENCY_STOP.ACTIVE"} <= set(ids)
    assert ids["ALM.PROCESS_PP1.ACTIVE"]["description"].endswith("- Temperatura kotla")
    assert "ALM.<alarm_id>.ACTIVE" not in ids
    assert "ALM.ANY_ACTIVE" in ids and "REQ.ALM.ACK_ALL" in ids

    # a second protection added later arrives after the next sync; a removed one leaves
    studio_project.process_protections.append(ProcessProtection(id="PP2", name="Cisnienie", analog_tag="ELA1.AI.2"))
    panel.sync_cards_from_studio(studio_project)
    assert "ALM.PROCESS_PP2.LATCHED" in {s["id"] for s in system_signals.get_all_signals(logic_project)}
    studio_project.process_protections = []
    studio_project.cards.append(Card(id="ADA1", model="ADA01", channel_kinds={"DO": 2}))
    panel.sync_cards_from_studio(studio_project)
    ids = {s["id"] for s in system_signals.get_all_signals(logic_project)}
    assert not any(i.startswith("ALM.PROCESS_") for i in ids)
    assert "ALM.PROT_SETTINGS_MISMATCH_ADA1.ACTIVE" in ids and "ALM.DEVICE_COMM_ADA1.ACTIVE" in ids
