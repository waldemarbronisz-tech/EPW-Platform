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
        # EPW_ACCESS_FILE: a bench/second-site override (see EPW_PROJECT_FILE).
        self.config_path = config_path or os.environ.get("EPW_ACCESS_FILE") or self.DEFAULT_CONFIG_PATH
        self.level = AccessLevel.USER
        self._pin_hashes = {}
        self._failed_attempts = {}  # level -> consecutive failure count
        self._lockout_until = {}  # level -> time.monotonic() timestamp

        # NAMED USERS (task "alarmówka: stopnie dostępu"). A level answers
        # "how much may whoever is standing here do"; it cannot answer
        # "only Kowalski may disarm the warehouse", because two operators
        # are the same Operator to it.
        #
        # The split is deliberate and load-bearing: WHO EXISTS and WHAT
        # THEY MAY DO come from the project (it travels to Studio, into
        # git, over REST - where a person's name belongs and their code
        # does not), while THEIR CODE lives only here, in this
        # controller's own gitignored access file, keyed by user id. So a
        # user exists the moment the project lands and can sign in the
        # moment someone sets their code ON the panel.
        self._users = {}            # user_id -> {"id", "name", "level", "zones", "enabled"}
        self._user_pin_hashes = {}  # user_id -> sha256 of the keypad code
        # user_id -> sha256 of that person's REMOTE token. A separate
        # secret from their keypad code on purpose: the token lives in a
        # Home Assistant automation on another machine, so a leak there
        # must not hand anyone the code that opens the panel standing in
        # front of the cabinet. High-entropy and machine-generated
        # (issue_remote_token()), never typed by a person.
        self._remote_token_hashes = {}
        # Who is signed in right now, or None for a plain level login
        # (the PIN-per-level path, which every installation starts on).
        self.current_user = None

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
                self._user_pin_hashes = data.get("user_pin_hashes", {}) or {}
                self._remote_token_hashes = data.get("remote_token_hashes", {}) or {}
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
            json.dump({"pin_hashes": self._pin_hashes,
                       "user_pin_hashes": self._user_pin_hashes,
                       "remote_token_hashes": self._remote_token_hashes}, f, indent=2)

    # --- named users ----------------------------------------------------

    def set_users(self, users) -> int:
        """Replaces the user registry with the project's own
        (shared/project_format.py's IntrusionUser). Codes are NOT touched:
        a user whose code was set on this panel keeps it across a project
        reinstall, and a user the project no longer has simply stops
        being able to sign in - their stored hash is dropped here so it
        cannot authorise anything.

        Returns how many usable records were taken."""
        registry = {}
        for raw in users or []:
            if not isinstance(raw, dict):
                continue
            user_id = str(raw.get("id") or "").strip()
            if not user_id:
                log.warning(f"Access user without an id ignored: {raw!r}")
                continue
            level = raw.get("level") or AccessLevel.OPERATOR
            if level not in AccessLevel._ORDER:
                log.warning(f"Access user {user_id!r} has an unrecognized level {level!r} - treated as User.")
                level = AccessLevel.USER
            registry[user_id] = {
                "id": user_id,
                "name": raw.get("name") or user_id,
                "level": level,
                "zones": list(raw.get("zones") or []),
                "enabled": bool(raw.get("enabled", True)),
            }
        self._users = registry
        orphaned = [uid for uid in set(self._user_pin_hashes) | set(self._remote_token_hashes)
                    if uid not in registry]
        for user_id in orphaned:
            self._user_pin_hashes.pop(user_id, None)
            self._remote_token_hashes.pop(user_id, None)
        if orphaned:
            log.warning(f"Dropped the stored code of {len(orphaned)} user(s) the project no longer has.")
            self._save()
        return len(registry)

    def get_users(self) -> list:
        """Every configured user, each with whether a code has been set
        on this panel (never the code itself)."""
        return [dict(user,
                     has_pin=user["id"] in self._user_pin_hashes,
                     has_remote_token=user["id"] in self._remote_token_hashes)
                for user in self._users.values()]

    def get_user(self, user_id: str):
        user = self._users.get(user_id)
        return dict(user) if user else None

    def set_user_pin(self, user_id: str, pin: str, level: str = None) -> bool:
        """Sets (or replaces) one user's code. Engineer level, like every
        other PIN change on this panel. Refused for a user the project
        does not define - a code with nobody behind it could never be
        audited to a person."""
        if level is not None and level != AccessLevel.ENGINEER:
            log.warning(f"Refused to set the code of user {user_id!r}: level {level!r} is below Engineer.")
            return False
        if user_id not in self._users:
            log.warning(f"Refused to set a code for unknown user {user_id!r}.")
            return False
        if not pin:
            log.warning(f"Refused to set an empty code for user {user_id!r}.")
            return False
        self._user_pin_hashes[user_id] = self._hash_pin(pin)
        self._save()
        log.info(f"Code set for user {self._users[user_id]['name']!r}.")
        return True

    def clear_user_pin(self, user_id: str, level: str = None) -> bool:
        """Takes a user's code away - they stay in the project (the event
        register still names them in past entries) but can no longer sign
        in."""
        if level is not None and level != AccessLevel.ENGINEER:
            log.warning(f"Refused to clear the code of user {user_id!r}: level {level!r} is below Engineer.")
            return False
        existed = self._user_pin_hashes.pop(user_id, None) is not None
        if existed:
            self._save()
        return existed

    def issue_remote_token(self, user_id: str, level: str = None):
        """Generates this person's REMOTE token and returns it ONCE.

        Only the hash is kept, so it can never be read back off the
        controller - the same one-way storage as every PIN here, and the
        same "shown exactly once" rule the REST API tokens follow. The
        caller shows it to the Engineer, who types it into that person's
        Home Assistant automation.

        Issuing again replaces the previous one: that is how a token
        that leaked is revoked - the old one stops working the moment
        the new one is generated.
        """
        if level is not None and level != AccessLevel.ENGINEER:
            log.warning(f"Refused to issue a remote token for {user_id!r}: level {level!r} is below Engineer.")
            return None
        if user_id not in self._users:
            log.warning(f"Refused to issue a remote token for unknown user {user_id!r}.")
            return None
        token = secrets.token_urlsafe(24)
        self._remote_token_hashes[user_id] = self._hash_pin(token)
        self._save()
        log.warning(f"Remote token issued for {self._users[user_id]['name']!r} - shown once, stored hashed.")
        return token

    def revoke_remote_token(self, user_id: str, level: str = None) -> bool:
        """Takes a person's remote access away without touching their
        keypad code - they keep working at the cabinet, they stop working
        from Home Assistant."""
        if level is not None and level != AccessLevel.ENGINEER:
            log.warning(f"Refused to revoke the remote token of {user_id!r}: level {level!r} is below Engineer.")
            return False
        existed = self._remote_token_hashes.pop(user_id, None) is not None
        if existed:
            self._save()
            log.warning(f"Remote token revoked for user {user_id!r}.")
        return existed

    def resolve_remote_token(self, token: str):
        """The person a remote token belongs to, or None.

        Pure lookup: NO session state changes, nothing is emitted, the
        panel's own access level is untouched. A command arriving over
        MQTT must not silently log anybody in at the cabinet - it carries
        its own identity for that one command and nothing more. Returns
        the user record (with their level and zones) so the caller can
        apply exactly the same rules the panel applies to that person.
        """
        if not token:
            return None
        hashed = self._hash_pin(token)
        for user_id, expected in self._remote_token_hashes.items():
            if not secrets.compare_digest(hashed, expected):
                continue
            user = self._users.get(user_id)
            if user is None or not user["enabled"]:
                return None
            return dict(user)
        return None

    def attempt_user_login(self, pin: str):
        """Signs in by CODE ALONE, the way a real alarm keypad works: the
        code identifies the person, and the person carries their own
        level. Returns the user record on success, None otherwise.

        The lockout is shared with that user's own level (the same
        counter attempt_login() uses), so guessing user codes cannot be
        used to sidestep it.
        """
        if not pin:
            return None
        hashed = self._hash_pin(pin)
        for user_id, expected in self._user_pin_hashes.items():
            if not secrets.compare_digest(hashed, expected):
                continue
            user = self._users.get(user_id)
            if user is None or not user["enabled"]:
                log.warning(f"Code accepted for user {user_id!r}, who is disabled or no longer in the project "
                            f"- refused.")
                self.event_bus.emit("login_attempt", AccessLevel.USER, False)
                return None
            level = user["level"]
            if self.is_locked_out(level):
                log.warning(f"Login rejected: {level} is locked out for another "
                            f"{self.lockout_remaining_seconds(level):.0f}s.")
                self.event_bus.emit("login_attempt", level, False)
                return None
            self.level = level
            self.current_user = dict(user)
            self._failed_attempts[level] = 0
            self.event_bus.emit("access_level_changed", level)
            self.event_bus.emit("login_attempt", level, True)
            log.info(f"{user['name']} signed in ({level}).")
            return dict(user)
        return None

    def current_user_id(self):
        """The signed-in person's id, or None when the session came from
        a plain level PIN. What the intrusion manager is handed as
        `user=` so that "only Kowalski may disarm the warehouse" can be
        enforced - and what the event register names."""
        return self.current_user["id"] if self.current_user else None

    def current_actor(self) -> str:
        """Who to record in the audit trail: the person if one signed in,
        otherwise the level that was used."""
        return self.current_user["name"] if self.current_user else self.level

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
            # A level PIN is nobody in particular - whoever was signed in
            # before is no longer the person at the keypad.
            self.current_user = None
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
            # Stepping down ends the named session too: whoever signed in
            # is no longer holding the level they signed in for, and the
            # event register must not keep crediting them.
            self.current_user = None
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
