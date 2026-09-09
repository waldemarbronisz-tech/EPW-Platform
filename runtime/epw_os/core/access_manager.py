import hashlib
import json
import os
import secrets
import time

from epw_os.core.logging import log


class AccessLevel:
    USER = "User"
    OPERATOR = "Operator"
    ENGINEER = "Engineer"

    # Ordered least to most privileged - has_access() compares indices here.
    _ORDER = [USER, OPERATOR, ENGINEER]


class AccessManager:
    """
    Headless (no PyQt) 3-level access control: User (default, no PIN,
    view-only) / Operator (PIN, HMI control) / Engineer (PIN, full access -
    Protection Settings, manual Force override).

    PINs are never stored or logged in plaintext after first generation.
    Only their SHA-256 hash lives in the on-disk config, which is gitignored.
    """

    # Absolute, anchored to this file's own location - NOT relative to the
    # process's current working directory. A relative path here silently
    # creates (and reads from) a *different* file depending on where the
    # app happens to be launched from (e.g. a multi-root VS Code workspace
    # whose integrated terminal cwd is the workspace root, not EPW-OS/,
    # runs `python EPW-OS/main.py` from one level up). Every such launch
    # would regenerate a brand-new access.local.json with brand-new random
    # PINs, silently orphaning whatever PIN was shown in an earlier run's
    # log - this was the actual cause of reported "PINs don't work" reports,
    # confirmed by reproducing it: launching from the repo's parent
    # directory created a second, separate config file with different PINs.
    DEFAULT_CONFIG_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "access.local.json"
    )

    # Brute-force lockout (Audit finding: a 4-digit PIN with unlimited,
    # unthrottled attempts is 10000 guesses away from Operator/Engineer
    # access - fine against a human on a touchscreen, not against
    # anything scripted). After LOCKOUT_THRESHOLD consecutive failures at
    # a given level, that level stops accepting ANY PIN - even a correct
    # one - for LOCKOUT_SECONDS. Per-level, not global: a lockout on
    # Operator does not affect Engineer, and vice versa. Resets to zero
    # on any successful login at that level.
    LOCKOUT_THRESHOLD = 5
    LOCKOUT_SECONDS = 30

    def __init__(self, event_bus, config_path: str = None):
        self.event_bus = event_bus
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self.level = AccessLevel.USER
        self._pin_hashes = {}
        self._failed_attempts = {}  # level -> consecutive failure count
        self._lockout_until = {}  # level -> time.monotonic() timestamp
        self._load_or_create_config()

    # --- persistence -------------------------------------------------

    @staticmethod
    def _hash_pin(pin: str) -> str:
        return hashlib.sha256(pin.encode("utf-8")).hexdigest()

    def _load_or_create_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    data = json.load(f)
                self._pin_hashes = data.get("pin_hashes", {})
                return
            except Exception as e:
                log.error(f"Failed to read {self.config_path}: {e}. Regenerating defaults.")

        # First run (or unreadable file): generate random PINs so there is
        # no fixed, predictable default anywhere in the codebase or docs.
        # They are shown exactly once, here, so the operator can retrieve
        # and then immediately change them via Settings.
        operator_pin = f"{secrets.randbelow(10000):04d}"
        engineer_pin = f"{secrets.randbelow(10000):04d}"
        self._pin_hashes = {
            AccessLevel.OPERATOR: self._hash_pin(operator_pin),
            AccessLevel.ENGINEER: self._hash_pin(engineer_pin),
        }
        self._save()

        log.warning("=" * 70)
        log.warning(f"No access config found - generated {self.config_path}")
        log.warning(f"  Default Operator PIN: {operator_pin}")
        log.warning(f"  Default Engineer PIN: {engineer_pin}")
        log.warning("CHANGE THESE PINs IN SETTINGS BEFORE PRODUCTION USE.")
        log.warning("This file is gitignored - PINs never enter source control.")
        log.warning("=" * 70)

    def _save(self):
        os.makedirs(os.path.dirname(self.config_path) or ".", exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump({"pin_hashes": self._pin_hashes}, f, indent=2)

    # --- session state -------------------------------------------------

    def has_access(self, required_level: str) -> bool:
        try:
            return AccessLevel._ORDER.index(self.level) >= AccessLevel._ORDER.index(required_level)
        except ValueError:
            # self.level is always one of this class's own AccessLevel
            # constants - only `required_level` (always a caller-supplied
            # literal) can realistically be the unrecognized one. Denying
            # access is the right fail-closed behavior either way (kept
            # unchanged), but a caller passing a bad level string is a
            # bug worth knowing about - the exact "silently does nothing,
            # nobody notices" shape the System.Mode tag-registration bug
            # had (Task: "polykane wyjatki").
            log.warning(f"has_access() got an unrecognized level {required_level!r} (self.level={self.level!r}) "
                        f"- denying access.")
            return False

    def is_locked_out(self, level: str) -> bool:
        return time.monotonic() < self._lockout_until.get(level, 0.0)

    def lockout_remaining_seconds(self, level: str) -> float:
        """Seconds left in `level`'s lockout, or 0.0 if it isn't locked
        out. For a future GUI hook (e.g. showing a countdown on the PIN
        prompt) - not used by the current login flow itself, which just
        needs the bool from is_locked_out()."""
        return max(0.0, self._lockout_until.get(level, 0.0) - time.monotonic())

    def attempt_login(self, level: str, pin: str) -> bool:
        if self.is_locked_out(level):
            # Deliberately rejected before even looking at the PIN -
            # entering the *correct* PIN must not quietly succeed and
            # skip the lockout, or the lockout would only ever stop
            # someone who kept guessing wrong.
            log.warning(f"Login rejected: {level} is locked out for another "
                        f"{self.lockout_remaining_seconds(level):.0f}s after "
                        f"{self.LOCKOUT_THRESHOLD} consecutive failed attempts.")
            self.event_bus.emit("login_attempt", level, False)
            return False

        expected = self._pin_hashes.get(level)
        if expected is not None and secrets.compare_digest(self._hash_pin(pin), expected):
            self.level = level
            self._failed_attempts[level] = 0
            self.event_bus.emit("access_level_changed", level)
            self.event_bus.emit("login_attempt", level, True)
            return True

        if expected is not None:
            # Only a real, known level counts towards the lockout - an
            # unknown `level` string can't be brute-forced into anything.
            count = self._failed_attempts.get(level, 0) + 1
            self._failed_attempts[level] = count
            if count >= self.LOCKOUT_THRESHOLD:
                self._lockout_until[level] = time.monotonic() + self.LOCKOUT_SECONDS
                self._failed_attempts[level] = 0
                log.warning(f"{level} locked out for {self.LOCKOUT_SECONDS}s after "
                            f"{self.LOCKOUT_THRESHOLD} consecutive failed PIN attempts.")
                self.event_bus.emit("login_lockout", level, self.LOCKOUT_SECONDS)
        self.event_bus.emit("login_attempt", level, False)
        return False

    def logout(self):
        self.demote(AccessLevel.USER)

    def demote(self, level: str) -> bool:
        """Voluntarily move to a level at or below the current one - e.g.
        the top-bar access selector, where picking a lower level than
        you're already at should just work. Never needs a PIN, since
        giving up privilege you already hold doesn't require proving
        anything. Refuses (returns False, no state change) if `level` is
        *above* the current level - elevation only ever happens through
        attempt_login()."""
        try:
            if AccessLevel._ORDER.index(level) > AccessLevel._ORDER.index(self.level):
                return False
        except ValueError:
            # Same reasoning as has_access() above - `level` is always
            # caller-supplied; an unrecognized value is refused (kept
            # unchanged) but is worth a log line, not silence.
            log.warning(f"demote() got an unrecognized level {level!r} - refusing.")
            return False
        if level != self.level:
            self.level = level
            self.event_bus.emit("access_level_changed", level)
        return True

    def verify_pin(self, level: str, pin: str) -> bool:
        """Pure check against the stored hash - no session-state side
        effects (unlike attempt_login). Used by the Settings PIN-change
        form to confirm the *old* PIN before accepting a new one."""
        expected = self._pin_hashes.get(level)
        return expected is not None and secrets.compare_digest(self._hash_pin(pin), expected)

    def set_pin(self, level: str, new_pin: str) -> bool:
        """Change a level's PIN. Caller (GUI) must already have verified
        the change is authorized - either has_access(level), or (Settings
        PIN-change form) a successful verify_pin(level, old_pin) - before
        calling this."""
        if level not in (AccessLevel.OPERATOR, AccessLevel.ENGINEER):
            return False
        self._pin_hashes[level] = self._hash_pin(new_pin)
        self._save()
        self.event_bus.emit("pin_changed", level)
        return True

    # --- future integration hook ----------------------------------------

    def can_control_via_synoptic(self) -> bool:
        """The Synoptic renderer doesn't exist in EPW-OS yet, but when it
        does, HMI control from it should require Operator-or-above - the
        same rule as everywhere else. Call this from that future code
        instead of re-deriving the access rule there."""
        return self.has_access(AccessLevel.OPERATOR)
