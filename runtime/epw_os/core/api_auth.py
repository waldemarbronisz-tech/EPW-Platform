"""REST API authentication (Task: "zamknac luke bezpieczenstwa w REST
API" - patrz BLAD 1: epw_os/backend/api.py wolalo CommandManager
bezposrednio, z pominieciem kazdej bramki uprawnien, wiec kazdy z
dostepem do portu mogl wydac dowolny rozkaz bez PIN-u).

Headless (no PyQt), same storage pattern AccessManager already uses for
PINs (epw_os/core/access_manager.py): a high-entropy secret per level
that can matter over the API, hashed with SHA-256, stored in a
gitignored local config file, auto-generated at first run and shown
EXACTLY ONCE in the startup log. Deliberately a SEPARATE module/file
from AccessManager, not an extension of it - GRANICE forbids touching
the PIN mechanism itself, and the two have genuinely different identity
models (see module docstring in epw_os/backend/api.py for why a plain
token-per-level, not PINs or sessions, was chosen here).

Only Operator and Engineer get a token. User never needs one: viewing
is always available with no PIN in the GUI (see al_matrix.md), and the
same rule applies here - a request presenting no token (or one that
resolves to nothing) is treated as User-equivalent, exactly like an
operator who never entered a PIN on the physical HMI.

A token authenticates a LEVEL, not an identity - the caller says
nothing the system trusts about who they are (GRANICE: "poziom dostepu
wywolujacego musi byc ustalany przez system, a nie podawany w tresci
zapytania"). The audit trail records "API:<resolved level>", never
anything the request body itself claims.
"""
import hashlib
import json
import os
import secrets
from typing import Optional

from epw_os.core.logging import log


# Task: DODATKOWO - "jesli w konfiguracji ustawiono adres inny niz
# lokalny, program ma to WYRAZNIE zasygnalizowac przy starcie oraz w
# interfejsie". One shared definition of "local", used by both main.py
# (the startup log warning) and main_window.py (the status-bar
# indicator) so they can never disagree about what counts as exposed.
_LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


def is_local_host(host: str) -> bool:
    return (host or "").strip().lower() in _LOCAL_HOSTS


class ApiAuth:
    # Absolute, anchored to this file's own location - same reasoning as
    # AccessManager.DEFAULT_CONFIG_PATH (a relative path here would
    # silently create/read a different file depending on the process's
    # launch directory).
    DEFAULT_CONFIG_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "api_tokens.local.json"
    )

    # Levels that can ever authenticate over the API. User is
    # deliberately absent - see module docstring.
    _LEVELS = ("Operator", "Engineer")

    def __init__(self, config_path: str = None):
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self._token_hashes = {}
        self._load_or_create_config()

    # --- persistence -------------------------------------------------

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _load_or_create_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    data = json.load(f)
                self._token_hashes = data.get("token_hashes", {})
                return
            except Exception as e:
                log.error(f"Failed to read {self.config_path}: {e}. Regenerating defaults.")

        # First run (or unreadable file): generate high-entropy random
        # tokens - 32 bytes/64 hex chars, not a 4-digit PIN, since these
        # are typed by nothing but a script/integration, never by a
        # person on a touchscreen, so there is no reason to keep them
        # short. Shown exactly once, here, so whoever deploys the API
        # integration can retrieve them immediately after this boot.
        tokens = {level: secrets.token_hex(32) for level in self._LEVELS}
        self._token_hashes = {level: self._hash_token(t) for level, t in tokens.items()}
        self._save()

        log.warning("=" * 70)
        log.warning(f"No API auth config found - generated {self.config_path}")
        for level, token in tokens.items():
            log.warning(f"  {level} API token: {token}")
        log.warning("Use as: Authorization: Bearer <token>")
        log.warning("This file is gitignored - tokens never enter source control.")
        log.warning("Lost a token? Delete this file and restart to regenerate both.")
        log.warning("=" * 70)

    def _save(self):
        os.makedirs(os.path.dirname(self.config_path) or ".", exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump({"token_hashes": self._token_hashes}, f, indent=2)

    # --- resolution ----------------------------------------------------

    def resolve_level(self, token: Optional[str]) -> Optional[str]:
        """The access level a presented token authenticates as, or None
        if it matches nothing (including an empty/missing token - never
        a match by construction, since a token is never hashed to the
        empty string). Checked highest-privilege first so an Engineer
        token is never mistakenly reported as merely Operator by an
        earlier, coincidental match - not that SHA-256 collisions are a
        real concern, but the check order should say what it means
        regardless."""
        if not token:
            return None
        token_hash = self._hash_token(token)
        for level in ("Engineer", "Operator"):
            expected = self._token_hashes.get(level)
            if expected is not None and secrets.compare_digest(token_hash, expected):
                return level
        return None

    @staticmethod
    def has_access(level: Optional[str], required_level: str) -> bool:
        """Pure ordering check, no session state - unlike
        AccessManager.has_access() (which reads a live, single, mutable
        "current session" level, the right model for one operator at one
        desktop), an API caller's level is resolved fresh from their own
        request's token every single call, since concurrent callers can
        legitimately hold different tokens at the same time. Reuses
        AccessLevel._ORDER (access_manager.py) as the one source of
        truth for level ordering rather than redefining it here."""
        from epw_os.core.access_manager import AccessLevel
        if level is None:
            level = AccessLevel.USER
        try:
            return AccessLevel._ORDER.index(level) >= AccessLevel._ORDER.index(required_level)
        except ValueError:
            # `level` is always either AccessLevel.USER (the default just
            # above) or whatever resolve_level() returned (always one of
            # its own known levels) - only `required_level` (a caller
            # literal) can realistically be unrecognized. Denying is the
            # right fail-closed behavior either way (kept unchanged), but
            # silently doing so hides a caller bug - same "polykane
            # wyjatki" pattern as System.Mode.
            log.warning(f"ApiAuth.has_access() got an unrecognized required_level {required_level!r} "
                        f"(level={level!r}) - denying access.")
            return False
