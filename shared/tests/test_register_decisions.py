"""The owner's decisions of 2026-09-24 on the register's open items:
function 32 has a stage, the functions the register had no summary bit
for have one, the older per-device names are gone with a signpost to
their register names, and the platform names he accepted are listed as
accepted in the status report."""
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from shared.docs import generate_signal_register_status as gen  # noqa: E402
from shared.logic import protection_stages as ps  # noqa: E402
from shared.logic import signal_renames, system_signals  # noqa: E402


def test_function_32_is_a_stage_appended_after_the_existing_ones():
    assert ps.STAGE_IDS[-1] == "RPWR_STAGE1" and ps.STAGE_INDEX["RPWR_STAGE1"] == 22
    assert ps.STAGE_INDEX["UV_STAGE1"] == 0 and ps.STAGE_INDEX["UPSV_STAGE1"] == 21, "existing addresses must not move"
    assert ps.stage_of_setting("32 Reverse Power", "Stage 1") == "RPWR_STAGE1"
    assert ps.stages_of_summary("PROT.POWER_REVERSE") == ["RPWR_STAGE1"]
    assert len(ps.STAGES) == 23


def test_every_stage_now_has_a_summary_bit_and_the_bits_are_in_the_catalogue():
    catalogue = {s["id"] for s in system_signals.raw_signals()}
    for stage_id, _ansi, _function, _stage, summaries in ps.STAGES:
        assert summaries, f"{stage_id} has no summary bit"
        for summary in summaries:
            assert summary in ps.SUMMARY_SIGNALS and summary in catalogue, summary
    assert ps.stages_of_summary("PROT.THERMAL_OVERLOAD") == ["THERMAL_STAGE1", "THERMAL_STAGE2"]
    assert ps.stages_of_summary("PROT.UPS_SUPPLY_LOSS") == ["UPSV_STAGE1"]
    # the two bits fed by one stage 47 stay two (owner: "zostaw dwa")
    assert ps.stages_of_summary("PROT.PHASE_LOSS") == ps.stages_of_summary("PROT.PHASE_SEQUENCE_FAULT") == ["PHSEQ_STAGE1"]


def test_the_function_catalogues_of_the_panel_and_the_studio_know_function_32():
    from studio.shell.project_panels import ELECTRICAL_PROTECTION_CATALOG
    assert any(function_id == "32 Reverse Power" for _c, function_id, _s, _u, _stages in ELECTRICAL_PROTECTION_CATALOG)
    sys.path.insert(0, str(_REPO_ROOT / "runtime"))
    from epw_os.core.protection_manager import ProtectionManager
    manager = ProtectionManager()
    manager.init_defaults()
    assert "32 Reverse Power" in manager.protections
    assert manager.protections["32 Reverse Power"].stages[0].name == "Stage 1"
    # every function the panel offers is a stage ADA01 can report
    for function_id, function in manager.protections.items():
        for stage in function.stages:
            assert ps.stage_of_setting(function_id, stage.name) is not None, (function_id, stage.name)


def test_the_older_per_device_names_are_not_in_the_catalogue_and_have_a_signpost():
    ids = {s["id"] for s in system_signals.raw_signals()}
    assert not any(i.split(".")[-1] == "SAFE_PATH_OK" for i in ids)
    assert signal_renames.legacy_device_signal("ELA1.ONLINE") == "COMM.ELA1.ONLINE"
    assert signal_renames.legacy_device_signal("ELA1.FAULT") == "COMM.ELA1.FAULT"
    assert signal_renames.legacy_device_signal("ADA1.SAFE_PATH_OK") == "DEV.ADA1.READY"
    assert signal_renames.legacy_device_signal("M.START") is None
    assert system_signals.get_catalog_version().split(".")[0] == "3", "removing names is a MAJOR bump"


def test_the_report_lists_the_accepted_platform_names_as_accepted():
    text = gen.build()
    head, _sep, tail = text.partition("## W katalogu, poza rejestrem — przyjęte przez właściciela")
    accepted_section = tail.partition("## W katalogu, poza rejestrem (")[0]
    for name in ("PROT.<stage_id>.LATCHED", "PROT.SETTINGS_MISMATCH", "PROT.THERMAL_OVERLOAD", "PROT.UPS_SUPPLY_LOSS"):
        assert f"`{name}` — przyjęte 2026-09-24" in accepted_section, name
    catalog = {gen._normalise(s["id"]): s for s in system_signals.raw_signals()}
    assert gen.classify({"ID / Wzorzec": "PROT.POWER_REVERSE", "Grupa": "PROTECTION"}, catalog, {})[0] == "w katalogu i obsłużony"


def test_the_alarm_instances_are_the_controllers_own_ids():
    from shared.logic.alarm_ids import alarm_instances
    cards = [{"id": "ELA1", "model": "ELA01"}, {"id": "ADA1", "model": "ADA01"}]
    protections = [{"id": "PP1", "name": "Temperatura kotla"}]
    ids = [a["id"] for a in alarm_instances(cards, protections)]
    assert ids[:4] == ["EMERGENCY_STOP", "SYSTEM_HEALTH", "REMOTE_COMMAND_REFUSED", "ALM_TEST"]
    assert ids[4:] == ["DEVICE_COMM_ELA1", "DEVICE_HEALTH_ELA1", "DEVICE_COMM_ADA1", "DEVICE_HEALTH_ADA1",
                       "PROT_SETTINGS_MISMATCH_ADA1", "PROCESS_PP1"]
    names = {a["id"]: a["name"] for a in alarm_instances(cards, protections)}
    assert names["PROCESS_PP1"] == "Temperatura kotla" and "ADA1" in names["PROT_SETTINGS_MISMATCH_ADA1"]
    assert len(ids) == len(set(ids))
    assert [a["id"] for a in alarm_instances([], [])] == ids[:4]
