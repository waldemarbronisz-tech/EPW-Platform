"""A backup of THIS controller, and the way back from a dead card.

Owner's instruction, after the survey that found there was no such
thing: a project is safe (it lives in Studio, in version control, and
can be sent over REST), but everything that belongs to the CONTROLLER
exists only on its own SD card. Switching counters that have been
running for four years. Which zones were armed when the power went. The
alarm memory. Line supervision. Retentive logic bits. The audit log -
the record of who did what. Lose the card and all of it is gone, and
there is no procedure, only somebody rebuilding it from memory.

## What a bundle holds

  meta         which controller, which project revision, when, by whom
  project      projekt.epw itself, so a bundle is self-sufficient
  state        runtime_state.json - counters, arming, alarm memory
  local        controller.local.json - language, REST, retentions, bus
  audit        the audit log, oldest first
  secrets      an INVENTORY: what existed, never a value

## What it does not hold, and why that is not a shortcut

**No secrets.** Not the PIN hashes, not the alarm users' keypad codes,
not the remote tokens, not the API tokens, not the MQTT broker
password.

A bundle is a file that leaves the site. It goes on a laptop, into a
mail attachment, onto a memory stick in a van. A PIN is four digits: a
hash of one is not a secret at all, it is a lookup table away from being
the PIN. Encrypting the bundle would answer that, but this controller
has no cryptography library and putting one on it to solve a problem
that can be avoided is the wrong trade - so it is avoided.

What the bundle carries instead is an **inventory**: which people had a
keypad code, which had a remote token, whether the API tokens and the
broker password were set. A restore then prints exactly what has to be
re-issued, by name. Re-issuing five codes from a checklist is ten
minutes. Recovering four years of switching counters is impossible.
That asymmetry is the whole argument.

**No historian.** Recorded measurements, not configuration, and
potentially gigabytes. A controller that comes back without its trend
history is working; one that comes back without its arming state is
lying about the building.

## What a restore does

Only what it can do honestly. The project goes in through the same path
as any other install, so the controller rebuilds itself from it
(EPWCore.reload_project) - no restart. The state file is written and the
alarm system re-reads it. The local settings are merged, never blindly
replaced: the new controller's own REST address and I/O driver describe
the hardware it is running on, not the hardware that died.

The arming state is restored **as it was written**, and the audit log
says so. A zone that was armed comes back armed. That is the same rule
the controller already applies to its own restart (SPEC: "uzbrojona
wstaje uzbrojona"), and a restore is a restart with extra steps.

Headless, standard library only, no Qt.
"""
import base64
import gzip
import hashlib
import json
import time
from pathlib import Path

from epw_os.core.local_json import atomic_write_json, read_json_object
from epw_os.core.logging import log

BACKUP_FORMAT = "EPW_CONTROLLER_BACKUP"
BACKUP_SCHEMA_VERSION = 1

# Files that hold a secret. Named here, once, so "which files must never
# go into a bundle" is a list somebody can read rather than a rule
# spread across three modules.
SECRET_FILES = ("access.local.json", "api_tokens.local.json", "mqtt.local.json")

# Local settings that describe the PHYSICAL controller rather than the
# installation - never taken from a bundle, because a replacement is
# different hardware on a different network. Everything else in
# controller.local.json is restored.
HARDWARE_LOCAL_KEYS = ("api", "io_driver", "logic_project", "synoptic_project")


class BackupError(Exception):
    """A bundle that cannot be read, or is not one of ours."""


def _checksum(payload: dict) -> str:
    """Over the canonical JSON of everything except the checksum itself
    - the same shape shared/logic/runtime_export.py already uses, so a
    truncated or edited bundle is refused rather than half-applied."""
    body = {key: value for key, value in payload.items() if key != "checksum"}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# --- building ---------------------------------------------------------------

def _secret_inventory(access_manager, project_manager, api_auth=None, mqtt_manager=None) -> dict:
    """Who had what, never what they had.

    This is the part that turns a restore into a checklist instead of a
    guess: "Kowalski had a keypad code and a remote token; Nowak had a
    code only" is exactly what somebody standing at a replacement
    controller needs, and none of it is a secret.

    Every question is put to the MANAGER that owns the answer, not to a
    guess about where its file is. The secret files do not sit next to
    projekt.epw - they live in epw_os/config/, each overridable by an
    environment variable, and only the manager knows which one it
    actually opened."""
    users = []
    if access_manager is not None:
        for user in (access_manager.get_users() or []):
            users.append({
                "id": user.get("id"),
                "name": user.get("name"),
                "level": user.get("level"),
                "had_code": bool(user.get("has_pin")),
                "had_remote_token": bool(user.get("has_remote_token")),
            })
    mqtt_config = project_manager.get_mqtt_config() if hasattr(project_manager, "get_mqtt_config") else {}
    return {
        "users": users,
        # The access levels always have PINs - a controller generates
        # random ones on first start rather than shipping defaults. So
        # this is not "were they set" but "the replacement has its own
        # random ones and nobody knows them": always true, always on
        # the checklist.
        "level_pins_set": ["Operator", "Engineer"],
        "api_tokens_set": _path_exists(getattr(api_auth, "config_path", None)),
        "mqtt_password_set": _path_exists(getattr(mqtt_manager, "secret_path", None)),
        "mqtt_broker": (mqtt_config or {}).get("host") or "",
    }


def _path_exists(path) -> bool:
    return bool(path) and Path(path).exists()


def _audit_rows(limit=None) -> list:
    """The audit log, oldest first. Read straight from the database - a
    backup taken while the controller runs must not depend on a manager
    being constructed."""
    try:
        from epw_os.db.database import SessionLocal
        from epw_os.db.models import AuditLog
    except Exception as e:  # a controller without the database module
        log.warning(f"Backup: the audit log could not be read ({e}).")
        return []
    session = SessionLocal()
    try:
        query = session.query(AuditLog).order_by(AuditLog.id.asc())
        if limit:
            query = query.limit(limit)
        return [{
            "timestamp": row.timestamp.isoformat() if row.timestamp else None,
            "event_type": row.event_type,
            "actor": row.actor,
            "detail": row.detail,
            "success": bool(row.success),
        } for row in query.all()]
    except Exception as e:
        log.warning(f"Backup: the audit log could not be read ({e}).")
        return []
    finally:
        session.close()


def build_backup(project_manager, access_manager=None, actor="SYSTEM",
                 include_audit=True, api_auth=None, mqtt_manager=None) -> bytes:
    """The bundle, gzipped JSON, ready to be written to a file or sent
    over REST. Never raises for a missing optional part - a controller
    with no state file yet still produces a valid backup of what it
    does have."""
    directory = Path(project_manager.project_file).parent
    header = project_manager.get_project_header() if hasattr(project_manager, "get_project_header") else {}

    project_bytes = None
    if hasattr(project_manager, "project_file_bytes"):
        project_bytes = project_manager.project_file_bytes()

    state, _problem = read_json_object(directory / "runtime_state.json")
    local, _problem_local = read_json_object(directory / "controller.local.json")

    payload = {
        "format": BACKUP_FORMAT,
        "schema_version": BACKUP_SCHEMA_VERSION,
        "meta": {
            "created_at": time.time(),
            "created_by": actor,
            "project_name": (header.get("name") or ""),
            "project_revision": header.get("revision"),
            "project_file": str(project_manager.project_file),
        },
        "project": base64.b64encode(project_bytes).decode("ascii") if project_bytes else None,
        "state": state or {},
        "local": local or {},
        "audit": _audit_rows() if include_audit else [],
        "secrets": _secret_inventory(access_manager, project_manager, api_auth, mqtt_manager),
    }
    payload["checksum"] = _checksum(payload)
    return gzip.compress(json.dumps(payload, ensure_ascii=False).encode("utf-8"))


# --- reading ----------------------------------------------------------------

def read_backup(data: bytes) -> dict:
    """The bundle as a dict, or BackupError with a reason a person can
    act on. Every failure here is a refusal to restore, never a partial
    one."""
    try:
        text = gzip.decompress(data).decode("utf-8")
    except (OSError, EOFError, UnicodeDecodeError) as e:
        raise BackupError(f"this is not a readable backup file ({e})") from e
    try:
        payload = json.loads(text)
    except ValueError as e:
        raise BackupError(f"the backup file is damaged ({e})") from e
    if not isinstance(payload, dict) or payload.get("format") != BACKUP_FORMAT:
        raise BackupError("this file is not an EPW controller backup")
    version = payload.get("schema_version")
    if version != BACKUP_SCHEMA_VERSION:
        raise BackupError(f"this backup was written by a different version of EPW-OS "
                          f"(schema {version}, this controller reads {BACKUP_SCHEMA_VERSION})")
    if payload.get("checksum") != _checksum(payload):
        raise BackupError("the backup file has been altered or truncated since it was written")
    return payload


def describe_backup(payload: dict) -> dict:
    """What is in a bundle, for showing somebody BEFORE they apply it -
    a restore overwrites a running controller, so it has to be possible
    to look first."""
    meta = payload.get("meta") or {}
    secrets = payload.get("secrets") or {}
    state = payload.get("state") or {}
    return {
        "created_at": meta.get("created_at"),
        "created_by": meta.get("created_by"),
        "project_name": meta.get("project_name"),
        "project_revision": meta.get("project_revision"),
        "has_project": bool(payload.get("project")),
        "counters": len((state.get("switching_counters") or {})),
        "armed_zones": list((state.get("intrusion_state") or {}).get("armed_zones") or []),
        "audit_entries": len(payload.get("audit") or []),
        "users_to_reissue": [user["name"] for user in (secrets.get("users") or [])
                             if user.get("had_code") or user.get("had_remote_token")],
        "api_tokens_to_reissue": bool(secrets.get("api_tokens_set")),
        "mqtt_password_to_reenter": bool(secrets.get("mqtt_password_set")),
    }


def reissue_checklist(payload: dict) -> list:
    """What a person has to do by hand after a restore, in the order
    they will do it. Plain data - the panel, Studio and the REST answer
    all render the same list rather than each inventing one."""
    secrets = payload.get("secrets") or {}
    items = []
    if secrets.get("level_pins_set"):
        items.append({"kind": "level_pins", "detail": ", ".join(secrets["level_pins_set"])})
    for user in (secrets.get("users") or []):
        needs = []
        if user.get("had_code"):
            needs.append("code")
        if user.get("had_remote_token"):
            needs.append("token")
        if needs:
            items.append({"kind": "user", "id": user.get("id"),
                          "detail": user.get("name") or user.get("id"), "needs": needs})
    if secrets.get("api_tokens_set"):
        items.append({"kind": "api_tokens", "detail": ""})
    if secrets.get("mqtt_password_set"):
        items.append({"kind": "mqtt_password", "detail": secrets.get("mqtt_broker") or ""})
    return items


# --- applying ---------------------------------------------------------------

def apply_backup(payload: dict, project_manager, actor="SYSTEM", restore_audit=False) -> dict:
    """Writes the bundle onto this controller's files.

    Does NOT rebuild the running controller - the caller does that
    through EPWCore.reload_project(), which is the one path that knows
    how to take a project into service. Keeping them apart is what lets
    this be tested without a whole core, and what stops a restore
    inventing a second way to install a project.

    Returns a report: what was written, what was skipped and why, and
    the checklist of what nobody can restore for you.
    """
    directory = Path(project_manager.project_file).parent
    written, skipped = [], []

    project_b64 = payload.get("project")
    if project_b64:
        target = Path(project_manager.project_file)
        try:
            if target.exists():
                backup_copy = target.with_suffix(target.suffix + ".bak")
                backup_copy.write_bytes(target.read_bytes())
            target.write_bytes(base64.b64decode(project_b64))
            written.append(target.name)
        except (OSError, ValueError) as e:
            skipped.append({"what": target.name, "why": str(e)})
    else:
        skipped.append({"what": "projekt.epw", "why": "the backup carries no project"})

    state = payload.get("state")
    if state:
        try:
            atomic_write_json(directory / "runtime_state.json", state)
            written.append("runtime_state.json")
        except OSError as e:
            skipped.append({"what": "runtime_state.json", "why": str(e)})

    # The local settings are MERGED, not replaced: a replacement
    # controller's REST address, I/O driver and file paths describe the
    # hardware it is actually running on.
    local = payload.get("local")
    if local:
        current, _problem = read_json_object(directory / "controller.local.json")
        merged = dict(current or {})
        for key, value in local.items():
            if key in HARDWARE_LOCAL_KEYS:
                skipped.append({"what": f"controller.local.json/{key}",
                                "why": "describes the hardware, not the installation"})
                continue
            merged[key] = value
        try:
            atomic_write_json(directory / "controller.local.json", merged)
            written.append("controller.local.json")
        except OSError as e:
            skipped.append({"what": "controller.local.json", "why": str(e)})

    if restore_audit:
        restored = _restore_audit(payload.get("audit") or [])
        written.append(f"audit log ({restored} entries)")

    for name in SECRET_FILES:
        skipped.append({"what": name, "why": "a backup never carries secrets"})

    log.warning(f"Controller restored from a backup by {actor}: "
                f"{len(written)} item(s) written, {len(skipped)} skipped.")
    return {"written": written, "skipped": skipped, "checklist": reissue_checklist(payload)}


def _restore_audit(rows) -> int:
    """Puts the backed-up audit entries back, oldest first, in front of
    whatever this controller has recorded since. Best effort: a failure
    here must not stop a restore that has already put the project and
    the state back."""
    if not rows:
        return 0
    try:
        from datetime import datetime

        from epw_os.db.database import SessionLocal
        from epw_os.db.models import AuditLog
    except Exception as e:
        log.warning(f"Restore: the audit log could not be written ({e}).")
        return 0
    session = SessionLocal()
    try:
        for row in rows:
            timestamp = None
            if row.get("timestamp"):
                try:
                    timestamp = datetime.fromisoformat(row["timestamp"])
                except ValueError:
                    timestamp = None
            session.add(AuditLog(
                timestamp=timestamp or datetime.now(),
                event_type=row.get("event_type") or "RESTORED_ENTRY",
                actor=row.get("actor") or "",
                detail=row.get("detail") or "",
                success=bool(row.get("success", True)),
            ))
        session.commit()
        return len(rows)
    except Exception as e:
        session.rollback()
        log.warning(f"Restore: the audit log could not be written ({e}).")
        return 0
    finally:
        session.close()
