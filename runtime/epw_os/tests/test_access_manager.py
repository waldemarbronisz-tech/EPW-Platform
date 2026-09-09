"""Tests for AccessManager's PIN verification and brute-force lockout
(Audit finding: PIN comparison used a plain `==` instead of
secrets.compare_digest, and attempt_login() had no limit at all on
consecutive failed attempts against a 4-digit PIN)."""
import pytest

from epw_os.core.access_manager import AccessManager, AccessLevel
from epw_os.core.events import EventBus


@pytest.fixture
def am(tmp_path):
    manager = AccessManager(EventBus(), config_path=str(tmp_path / "access.local.json"))
    # _load_or_create_config() already generated random PINs and hashed
    # them - overwrite with known values so tests don't have to scrape
    # them back out of the log.
    manager._pin_hashes = {
        AccessLevel.OPERATOR: manager._hash_pin("1111"),
        AccessLevel.ENGINEER: manager._hash_pin("2222"),
    }
    return manager


def test_correct_pin_logs_in(am):
    assert am.attempt_login(AccessLevel.OPERATOR, "1111") is True
    assert am.level == AccessLevel.OPERATOR


def test_wrong_pin_rejected_and_level_unchanged(am):
    assert am.attempt_login(AccessLevel.OPERATOR, "0000") is False
    assert am.level == AccessLevel.USER


def test_unknown_level_never_matches_and_never_crashes(am):
    assert am.attempt_login("NotALevel", "1111") is False


def test_login_attempt_event_fires_with_correct_success_flag(am):
    seen = []
    am.event_bus.subscribe("login_attempt", lambda level, success: seen.append((level, success)))
    am.attempt_login(AccessLevel.OPERATOR, "0000")
    am.attempt_login(AccessLevel.OPERATOR, "1111")
    assert seen == [(AccessLevel.OPERATOR, False), (AccessLevel.OPERATOR, True)]


def test_lockout_after_threshold_consecutive_failures(am):
    for _ in range(AccessManager.LOCKOUT_THRESHOLD):
        assert am.attempt_login(AccessLevel.OPERATOR, "0000") is False
    assert am.is_locked_out(AccessLevel.OPERATOR) is True
    # Even the CORRECT pin must be rejected while locked out - otherwise
    # the lockout only ever stops someone who keeps guessing wrong.
    assert am.attempt_login(AccessLevel.OPERATOR, "1111") is False
    assert am.level == AccessLevel.USER


def test_lockout_emits_login_lockout_event_once(am):
    fired = []
    am.event_bus.subscribe("login_lockout", lambda level, duration: fired.append((level, duration)))
    for _ in range(AccessManager.LOCKOUT_THRESHOLD):
        am.attempt_login(AccessLevel.OPERATOR, "0000")
    assert fired == [(AccessLevel.OPERATOR, AccessManager.LOCKOUT_SECONDS)]
    # One more failure while already locked out must not re-fire it.
    am.attempt_login(AccessLevel.OPERATOR, "0000")
    assert fired == [(AccessLevel.OPERATOR, AccessManager.LOCKOUT_SECONDS)]


def test_lockout_is_per_level_not_global(am):
    for _ in range(AccessManager.LOCKOUT_THRESHOLD):
        am.attempt_login(AccessLevel.OPERATOR, "0000")
    assert am.is_locked_out(AccessLevel.OPERATOR) is True
    assert am.is_locked_out(AccessLevel.ENGINEER) is False
    assert am.attempt_login(AccessLevel.ENGINEER, "2222") is True


def test_successful_login_resets_failure_counter(am):
    # threshold - 1 failures, then a success, then threshold - 1 more
    # failures must NOT lock out - the counter should have reset.
    for _ in range(AccessManager.LOCKOUT_THRESHOLD - 1):
        am.attempt_login(AccessLevel.OPERATOR, "0000")
    assert am.attempt_login(AccessLevel.OPERATOR, "1111") is True
    am.demote(AccessLevel.USER)
    for _ in range(AccessManager.LOCKOUT_THRESHOLD - 1):
        am.attempt_login(AccessLevel.OPERATOR, "0000")
    assert am.is_locked_out(AccessLevel.OPERATOR) is False


def test_lockout_expires_after_its_duration(am, monkeypatch):
    import epw_os.core.access_manager as access_manager_module

    fake_now = [1000.0]
    monkeypatch.setattr(access_manager_module.time, "monotonic", lambda: fake_now[0])

    for _ in range(AccessManager.LOCKOUT_THRESHOLD):
        am.attempt_login(AccessLevel.OPERATOR, "0000")
    assert am.is_locked_out(AccessLevel.OPERATOR) is True

    fake_now[0] += AccessManager.LOCKOUT_SECONDS + 1
    assert am.is_locked_out(AccessLevel.OPERATOR) is False
    assert am.attempt_login(AccessLevel.OPERATOR, "1111") is True


def test_verify_pin_uses_constant_time_comparison_correctly(am):
    """Not a timing measurement (unreliable in a test suite) - just
    confirms the switch to secrets.compare_digest() didn't change
    verify_pin()'s actual correctness."""
    assert am.verify_pin(AccessLevel.OPERATOR, "1111") is True
    assert am.verify_pin(AccessLevel.OPERATOR, "1112") is False
    assert am.verify_pin(AccessLevel.OPERATOR, "") is False
    assert am.verify_pin("NotALevel", "1111") is False
