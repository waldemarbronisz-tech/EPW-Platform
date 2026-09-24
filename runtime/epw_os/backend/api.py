"""REST API (Task: "zamknac luke bezpieczenstwa w REST API").

Runs alongside the GUI, always, on its own thread (see main.py's
run_backend()) - so anything reachable here is reachable without ever
touching a PIN prompt in the desktop UI. Three real defects existed
before this task and are fixed here:

BLAD 1 (KRYTYCZNY): POST /api/v1/commands called
CommandManager.request_command() directly, with zero access-level
check anywhere in the chain (CommandManager itself checks only
safety_kernel/logic_engine - never access level; that gate lives
entirely in GUI click handlers, which this endpoint bypassed
completely) - anyone reaching the port could issue any command with no
PIN and no level. Fixed by requiring a bearer token (Authorization:
Bearer <token>) resolved through the new ApiAuth
(epw_os/core/api_auth.py) - see that module's own docstring for the
full design and epw_os/help/{en,pl}/api_what.md / SESSION_REPORT.md for
the authentication-mechanism trade-off writeup. The caller's level is
determined ENTIRELY by which token they present - the old "user" field
in the request body, which the audit log simply believed, is gone.

BLAD 2: GET /api/v1/tags iterated a hardcoded empty list
("for name, tag in []") - always returned []. Fixed: reads
TagManager.list_tags() for real, with an optional "?prefix=" filter
(the tag count in this app is a few hundred, not enough to justify
real pagination - see SESSION_REPORT.md for the sizing reasoning).

BLAD 4: POST /api/v1/commands ended on a bare "pass" (returning null)
whenever a command was actually accepted - the caller got no
confirmation, no command id, nothing. Fixed: returns the real
CommandRecord's id/state/reason/timestamp, using
request_command_ex() (the exact same dispatch path the GUI's own Force
buttons use, not the older request_command() wrapper) so the response
reflects the real, full command lifecycle, not a boolean summary of it.

GET endpoints (health/tags/alarms) stay unauthenticated on purpose:
they are read-only, and every GUI page in this app is viewable at User
level with no PIN at all (see al_matrix.md) - an unauthenticated API
caller is exactly a User-equivalent, and User already sees this much
in the GUI. Only a genuinely state-changing endpoint - today, only
POST /api/v1/commands - requires authentication (GRANICE's own
wording: "Endpointy ZMIENIAJACE STAN... MUSZA wymagac
uwierzytelnienia").
"""
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Request, Header, Response
from pydantic import BaseModel
import logging
import os
import tempfile
import threading
import time

from epw_os.core.access_manager import AccessLevel

app = FastAPI(title="EPW OS API")
logger = logging.getLogger("API")


# Models
class ForceRequest(BaseModel):
    tag: str
    value: object


class BitWriteRequest(BaseModel):
    value: object


class ProtectionTestRequest(BaseModel):
    kind: str        # "process" | "apparatus"
    id: str          # the process protection's id, or the apparatus id


class ModeRequest(BaseModel):
    mode: str        # core/operating_mode.py MODES


class CommandRequest(BaseModel):
    device_tag: str
    command: str
    # Deliberately no "user" field (Task, BLAD 1 - nonnegotiable
    # requirement: "Pole 'user' w obecnej postaci ma zniknac albo
    # przestac miec znaczenie dla uprawnien"). The caller's identity is
    # the access level their bearer token resolves to - see
    # _require_operator() below - never anything the request body says.


# Dependency to retrieve the shared headless EPWCore
def get_core(request: Request):
    if not hasattr(request.app.state, "core"):
        raise HTTPException(status_code=503, detail="EPWCore not bound to API state.")
    return request.app.state.core


def _require_operator(core=Depends(get_core), authorization: Optional[str] = Header(None)) -> str:
    """FastAPI dependency gating any state-changing endpoint (today:
    POST /api/v1/commands) at Operator or above - the same rule
    mv_control.md documents for the GUI's own Force buttons ("User nie
    steruje. Kropka" - GRANICE). The level comes ENTIRELY from
    core.api_auth.resolve_level(token); a missing, malformed, or
    unrecognized token resolves to None/User, exactly like an operator
    who never entered a PIN on the physical HMI. Every rejection here
    - not just a missing header, but also a valid-but-insufficient
    token, should one ever exist for a level below Operator - is logged
    to the audit trail as a failed authentication (Task, DOWOD:
    "nieudane proby uwierzytelnienia trafiaja do dziennika
    audytowego"), with the level actually resolved (or None) as the
    recorded actor - never a client-supplied name."""
    return _resolve_or_reject(core, authorization, AccessLevel.OPERATOR, "POST /api/v1/commands")


def _require_engineer(core=Depends(get_core), authorization: Optional[str] = Header(None)) -> str:
    """Engineer gate for the project endpoints (task "wysyłanie projektu
    na sterownik przez REST": "tokenu na poziomie Engineer") - the same
    rule the panel's own File > Open (install) applies."""
    return _resolve_or_reject(core, authorization, AccessLevel.ENGINEER, "project install/download")


def _resolve_or_reject(core, authorization, required_level, what: str) -> str:
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    level = core.api_auth.resolve_level(token)
    if not core.api_auth.has_access(level, required_level):
        actor = f"API:{level}" if level else "API (no/invalid token)"
        if core.audit_logger is not None:
            core.audit_logger.record(
                "API_AUTH_FAILED", actor,
                f"{what} requires {required_level} level or higher", success=False,
            )
        raise HTTPException(
            status_code=401,
            detail=f"Valid {required_level} (or higher) API token required (Authorization: Bearer <token>)",
        )
    return level


@app.get("/api/v1/health")
def get_health(core=Depends(get_core)):
    """Returns the subsystem health states."""
    return {
        "status": "UP" if core.is_running else "DOWN",
        "subsystems": core.health_manager.get_health(),
    }


@app.get("/api/v1/logic")
def get_logic(core=Depends(get_core)):
    """What the logic program is doing right now: whether a program is
    loaded at all, whether the scan is running, its cycle time, how many
    scans it has run, the longest one, which outputs it drives and why it
    is not running if it is not.

    /api/v1/health only ever says RUNNING/FAULT/DEGRADED for the whole
    subsystem - true but not enough to tell "no logic in this project"
    from "the program was refused". Read-only and unauthenticated, like
    the other views (forces, alarms): what the controller is executing is
    deliberately visible to everyone.
    """
    engine = getattr(core, "logic_engine", None)
    if engine is None:
        raise HTTPException(status_code=404, detail="This controller has no logic engine.")
    return engine.get_status()


@app.post("/api/v1/logic/reload")
def reload_logic(core=Depends(get_core), level: str = Depends(_require_engineer)):
    """Puts the project's current logic program into the scan without
    restarting the controller (Engineer token, audited) - see
    EPWCore.reload_logic()."""
    result = core.reload_logic(actor=f"API:{level}", level=None)
    if not result["success"]:
        raise HTTPException(status_code=409, detail={"error": "logic_reload_failed",
                                                     "reason": result["reason"],
                                                     "status": result["status"]})
    return result


@app.get("/api/v1/tags")
def get_tags(core=Depends(get_core), prefix: Optional[str] = None):
    """Returns current tag values and qualities. BLAD 2 fix: this used
    to iterate a hardcoded empty list and always return [] - now reads
    the real TagManager. Optional "?prefix=" narrows the result to tag
    names starting with that string (e.g. "?prefix=DI") - a few hundred
    tags is not enough to justify real pagination (see
    SESSION_REPORT.md), but a caller that only wants one device's worth
    of tags shouldn't have to filter the full list client-side."""
    tags = core.tag_manager.list_tags()
    if prefix:
        tags = [t for t in tags if t.name.startswith(prefix)]
    return [
        {
            "name": t.name,
            "value": t.value,
            "quality": t.quality.value,
            "data_type": t.data_type.value,
            "timestamp": t.timestamp,
        }
        for t in tags
    ]


@app.get("/api/v1/tags/export")
def export_tags(core=Depends(get_core)):
    """Signal (tag) list export for Logic Studio/Synoptic Editor (Task:
    "eksport listy wszystkich tagow systemowych do pliku... Eksport
    przez REST API... zeby Logic Studio moglo pobrac ja bez plikow, gdy
    sterownik jest dostepny"). Same structure the GUI's Tools > Export
    Signal List... menu action writes to a file (see
    epw_os.core.tag_export.build_tag_list_export() - the one function
    both paths call), just returned as a live response instead. Read-
    only, unauthenticated - same "GET endpoints stay unauthenticated on
    purpose, a caller here is exactly a User-equivalent" reasoning this
    module's own docstring already gives for /health, /tags, /alarms
    (Task: "uwierzytelnianie jak przy innych endpointach odczytu")."""
    from epw_os.core.tag_export import build_tag_list_export
    return build_tag_list_export(core.tag_manager, getattr(core, "project_manager", None))


@app.get("/api/v1/tags/{tag_name}")
def get_tag(tag_name: str, core=Depends(get_core)):
    """Returns a specific tag."""
    tag = core.tag_manager.get_tag(tag_name)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    return {
        "name": tag.name,
        "value": tag.value,
        "quality": tag.quality.value,
        "data_type": tag.data_type.value,
        "timestamp": tag.timestamp,
    }


@app.get("/api/v1/alarms")
def get_alarms(core=Depends(get_core)):
    """Returns all active alarms."""
    return [
        {
            "id": a.id,
            "message": a.message,
            "priority": a.priority,
            "state": a.state.value,
            "activation_time": a.activation_time,
        }
        for a in core.alarm_manager.get_active_alarms()
    ]


@app.get("/api/v1/project")
def get_project(core=Depends(get_core)):
    """Which project this controller runs and which revision of it (task
    "runtime czyta projekt.epw", 5.2): name, description, author, dates,
    `revision`, `modified_by` ("studio" or "panel"), the module
    composition and counts. What Studio reads before sending a project,
    so it can stop when the controller already holds a newer revision
    (SPEC_PROJEKT_EPW.md, "Wersjonowanie"). Read-only and unauthenticated
    - the same reasoning as /health, /tags and /alarms: nothing here is
    beyond what a User-level panel viewer already sees."""
    return core.project_manager.get_project_header()


@app.post("/api/v1/commands")
def issue_command(cmd: CommandRequest, core=Depends(get_core), level: str = Depends(_require_operator)):
    """Issues a command through the exact same path a real Force button
    uses (BLAD 4 fix: request_command_ex(), not the older
    request_command() wrapper - see module docstring) - full
    safety_kernel/logic_engine validation, no shortcut. "actor" is the
    access level the caller's bearer token resolved to - the identity
    that reaches CommandManager and the audit trail, never anything the
    request body claims (BLAD 1 - GRANICE: "dziennik audytowy ma
    zapisywac tozsamosc USTALONA przez system, a nie podawana w
    zapytaniu")."""
    actor = f"API:{level}"
    record = core.command_manager.request_command_ex(cmd.device_tag, cmd.command, user=actor, source="API")
    success = record.state not in ("BLOCKED", "FAILED")

    if core.audit_logger is not None:
        detail = f"{cmd.device_tag}.{cmd.command} -> {record.state}"
        if record.reason:
            detail += f" ({record.reason})"
        core.audit_logger.record("API_COMMAND", actor, detail, success=success)

    if not success:
        # BLAD 4 fix kept the ORIGINAL response shape for this path
        # (status 403, {"error", "reasons"}) - only the accepted path
        # below used to be broken (a bare "pass").
        raise HTTPException(status_code=403, detail={"error": "Command Blocked", "reasons": [record.reason]})

    return {
        "command_id": record.id,
        "state": record.state,
        "reason": record.reason,
        "requested_at": record.requested_at,
        "actor": actor,
    }


# --- the project file itself (task "wysyłanie projektu na sterownik przez REST") ----

@app.get("/api/v1/project/settings")
def get_project_settings(core=Depends(get_core)):
    """The controller's settings as {path: value} plus the header's
    revision/settings_hash - what Studio diffs against its own project
    before sending, to show "tu 25 A, tam 40 A" instead of overwriting
    (SPEC "Wersjonowanie"). Read-only, unauthenticated: every value here
    is on a panel page a User-level viewer already sees."""
    pm = core.project_manager
    project = getattr(pm, "project", None)
    header = pm.get_project_header()
    if project is None:
        return {"loaded": False, "revision": header.get("revision"), "settings_hash": None, "settings": {},
                "load_error": header.get("load_error")}
    from epw_os.core import project_format as pf
    return {"loaded": True, "revision": project.revision, "modified_by": project.modified_by,
            "settings_hash": pf.settings_hash(project), "settings": pf.settings_snapshot(project)}


@app.get("/api/v1/project/file")
def download_project_file(core=Depends(get_core), level: str = Depends(_require_engineer)):
    """projekt.epw exactly as it is on the controller ("Zgraj z
    urządzenia" - with the settings changed on the panel inside)."""
    payload = core.project_manager.project_file_bytes()
    if payload is None:
        raise HTTPException(status_code=404, detail="This controller has no projekt.epw.")
    if core.audit_logger is not None:
        core.audit_logger.record("API_PROJECT_DOWNLOADED", f"API:{level}", core.project_manager.project_file,
                                 success=True)
    return Response(content=payload, media_type="application/gzip",
                    headers={"Content-Disposition": 'attachment; filename="projekt.epw"'})


# --- forcing (SPEC "Wymuszanie stanów - dozwolone, obwarowane"; core/force_manager.py) -----

def _forces_body(manager) -> dict:
    return {"forces": manager.snapshot(), "heartbeat_timeout_s": manager.heartbeat_timeout_s,
            "seconds_since_heartbeat": manager.seconds_since_heartbeat()}


@app.get("/api/v1/forces")
def get_forces(core=Depends(get_core)):
    """Every active force - what Studio marks and what the panel's own
    indicator counts. Read-only, unauthenticated like the other views:
    a force is deliberately visible to everyone."""
    manager = getattr(core, "force_manager", None)
    if manager is None:
        return {"forces": [], "heartbeat_timeout_s": None, "seconds_since_heartbeat": None}
    return _forces_body(manager)


@app.post("/api/v1/forces")
def set_force(body: ForceRequest, core=Depends(get_core), level: str = Depends(_require_engineer)):
    """Pins an input or drives an output (Engineer token). Refused for
    anything off the project's points or on the protection path - the
    refusal is audited too. Counts as a heartbeat."""
    manager = getattr(core, "force_manager", None)
    if manager is None:
        raise HTTPException(status_code=404, detail="Forcing is not available on this controller.")
    ok, reason = manager.force(body.tag, body.value, actor=f"API:{level}")
    if not ok:
        raise HTTPException(status_code=403, detail={"error": "force_refused", "reason": reason})
    return {"forced": True, "tag": body.tag, "value": body.value, **_forces_body(manager)}


@app.post("/api/v1/bits/{bit_id}")
def write_internal_bit(bit_id: str, body: BitWriteRequest, core=Depends(get_core),
                       authorization: Optional[str] = Header(None)):
    """Sets an internal IN bit from outside the logic (internal bits
    IN/OUT). The gate decides: the bit must be IN, the project must
    allow remote writes to it, and the token's level must reach what the
    bit demands. Every write and refusal is audited by the gate."""
    gate = getattr(core, "internal_bits", None)
    if gate is None:
        raise HTTPException(status_code=404, detail="Internal bits are not available on this controller.")
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    level = core.api_auth.resolve_level(token)
    ok, reason = gate.write(bit_id, body.value, actor=level or "no token", source="REST", level=level)
    if not ok:
        raise HTTPException(status_code=403, detail={"error": "bit_write_refused", "reason": reason})
    tag = core.tag_manager.get_tag(bit_id)
    return {"written": True, "bit": bit_id, "value": tag.value if tag is not None else body.value}


@app.post("/api/v1/forces/heartbeat")
def force_heartbeat(core=Depends(get_core), level: str = Depends(_require_engineer)):
    """Studio calls this while it holds forces; silence for longer than
    heartbeat_timeout_s releases them all (a closed laptop, a lost
    link)."""
    manager = getattr(core, "force_manager", None)
    if manager is None:
        raise HTTPException(status_code=404, detail="Forcing is not available on this controller.")
    manager.heartbeat()
    return _forces_body(manager)


@app.delete("/api/v1/forces/{tag_name}")
def release_force(tag_name: str, core=Depends(get_core), level: str = Depends(_require_engineer)):
    manager = getattr(core, "force_manager", None)
    if manager is None or not manager.release(tag_name, actor=f"API:{level}"):
        raise HTTPException(status_code=404, detail=f"{tag_name} is not forced.")
    return {"released": True, "tag": tag_name, **_forces_body(manager)}


@app.delete("/api/v1/forces")
def release_all_forces(core=Depends(get_core), level: str = Depends(_require_engineer)):
    """"Zdjęcie wszystkiego jednym poleceniem"."""
    manager = getattr(core, "force_manager", None)
    if manager is None:
        raise HTTPException(status_code=404, detail="Forcing is not available on this controller.")
    count = manager.release_all(actor=f"API:{level}", reason="released from Studio")
    return {"released": count, **_forces_body(manager)}


# --- the operating mode (MODE.* / REQ.MODE.*, core/operating_mode.py) ----------------------

@app.get("/api/v1/mode")
def get_operating_mode(core=Depends(get_core)):
    """The controller's operating mode, the modes it knows and the level
    each one needs - the same table the panel and the logic use."""
    from epw_os.core import operating_mode as modes
    manager = getattr(core, "operating_mode", None)
    return {"mode": manager.mode if manager is not None else None, "modes": list(modes.MODES),
            "required_level": dict(modes.REQUIRED_LEVEL)}


@app.post("/api/v1/mode")
def set_operating_mode(body: ModeRequest, core=Depends(get_core), authorization: Optional[str] = Header(None)):
    """Changes the operating mode. The level the token resolves to must
    reach what the mode demands (Operator for NORMAL/AUTO/MANUAL/
    EMERGENCY, Engineer for SERVICE/MAINTENANCE/TEST) - refusals are
    audited, like every other refusal of this endpoint family."""
    from epw_os.core import operating_mode as modes
    manager = getattr(core, "operating_mode", None)
    if manager is None:
        raise HTTPException(status_code=404, detail="This controller has no operating mode manager.")
    if body.mode not in modes.MODES:
        raise HTTPException(status_code=400, detail={"error": "unknown_mode", "mode": body.mode,
                                                     "modes": list(modes.MODES)})
    level = _resolve_or_reject(core, authorization, modes.REQUIRED_LEVEL[body.mode], f"POST /api/v1/mode {body.mode}")
    ok, reason = manager.set_mode(body.mode, actor=f"API:{level}", level=level)
    if not ok:
        raise HTTPException(status_code=403, detail={"error": "mode_refused", "reason": reason})
    return {"mode": manager.mode}


# --- protection tests (SPEC "Wymuszanie stanów - Powiązanie": the internal Omicron) --------

@app.get("/api/v1/protection-tests")
def list_protection_tests(core=Depends(get_core)):
    """Every report kept on the controller, the test in progress and what
    can be tested (process protections, commandable apparatuses)."""
    runner = getattr(core, "protection_tests", None)
    if runner is None:
        return {"available": False, "reports": [], "running": None, "candidates": {"process": [], "apparatus": []}}
    return {"available": True, "reports": runner.list_reports(), "running": runner.running(),
            "candidates": runner.candidates()}


@app.post("/api/v1/protection-tests")
def start_protection_test(body: ProtectionTestRequest, core=Depends(get_core),
                          level: str = Depends(_require_engineer)):
    """Starts one test (Engineer token). Answers at once with the report
    as RUNNING (poll GET /api/v1/protection-tests/<id>) or BLOCKED."""
    runner = getattr(core, "protection_tests", None)
    if runner is None:
        raise HTTPException(status_code=404, detail="Protection tests are not available on this controller.")
    actor = f"API:{level}"
    if body.kind == "process":
        report = runner.start_process_test(body.id, actor=actor)
    elif body.kind == "apparatus":
        report = runner.start_apparatus_test(body.id, actor=actor)
    else:
        raise HTTPException(status_code=400, detail={"error": "unknown_kind", "kind": body.kind})
    if report["result"] == "BLOCKED":
        raise HTTPException(status_code=409, detail={"error": "test_blocked", "reason": report["reason"], "report": report})
    return report


@app.get("/api/v1/protection-tests/{test_id}")
def get_protection_test(test_id: str, core=Depends(get_core)):
    runner = getattr(core, "protection_tests", None)
    report = runner.get(test_id) if runner is not None else None
    if report is None:
        raise HTTPException(status_code=404, detail=f"No protection test {test_id}.")
    return report


@app.get("/api/v1/controller/backup")
def get_controller_backup(core=Depends(get_core), level: str = Depends(_require_engineer)):
    """This controller's own backup - everything that exists nowhere
    else: the switching counters, the arming state, the alarm memory,
    the retentive logic bits, the audit log, the local settings, and
    projekt.epw itself so the bundle is self-sufficient.

    It carries NO secret: no PIN hash, no alarm user's keypad code, no
    remote or API token, no broker password. A bundle is a file that
    leaves the site, and a four-digit PIN behind a hash is not a secret.
    What it carries instead is an inventory - who HAD a code, who had a
    token - so a restore can print exactly what to re-issue, by name.
    See core/controller_backup.py.

    Engineer token, audited."""
    actor = f"API:{level}"
    try:
        data = core.backup_bundle(actor=actor, level=None)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail={"error": "access_denied", "reason": str(e)})
    name = f"epw-backup-{int(time.time())}.epwbak"
    return Response(content=data, media_type="application/gzip",
                    headers={"content-disposition": f'attachment; filename="{name}"'})


@app.post("/api/v1/controller/backup/inspect")
async def inspect_controller_backup(request: Request, core=Depends(get_core),
                                     level: str = Depends(_require_engineer)):
    """What is in a bundle, without applying it. A restore overwrites a
    running controller, so it has to be possible to look first."""
    from epw_os.core import controller_backup

    payload = await request.body()
    if not payload:
        raise HTTPException(status_code=400, detail={"error": "empty_body"})
    try:
        bundle = controller_backup.read_backup(payload)
    except controller_backup.BackupError as e:
        raise HTTPException(status_code=400, detail={"error": "bad_backup", "reason": str(e)})
    return {"summary": controller_backup.describe_backup(bundle),
            "checklist": controller_backup.reissue_checklist(bundle)}


@app.post("/api/v1/controller/restore")
async def restore_controller(request: Request, restore_audit: bool = False,
                             core=Depends(get_core), level: str = Depends(_require_engineer)):
    """Puts a backup onto this controller and takes the restored project
    into service, without restarting (the same rebuild an install goes
    through - see EPWCore.reload_project).

    A bundle that cannot be trusted - wrong format, wrong schema
    version, altered since it was written - is refused before anything
    is written. A restore is never half-applied.

    The answer carries `checklist`: the secrets nobody can restore for
    you, by name. Engineer token, audited."""
    actor = f"API:{level}"
    payload = await request.body()
    if not payload:
        raise HTTPException(status_code=400, detail={"error": "empty_body"})
    result = core.restore_from_backup(payload, actor=actor, level=None,
                                       restore_audit=bool(restore_audit))
    if not result.get("success") and result.get("reason"):
        raise HTTPException(status_code=400, detail={"error": "restore_failed",
                                                     "reason": result["reason"],
                                                     "checklist": result.get("checklist", [])})
    return result


@app.get("/api/v1/controller/settings")
def get_controller_settings(core=Depends(get_core)):
    """What stays on THIS controller and is not in the project
    (controller.local.json: language, REST host/port, retentions, the
    database size warning, the I/O driver, file paths) - read-only, so
    Studio can show everything the controller holds ("Studio powinno
    móc zaczytać kompletnie wszystkie informacje ze sterownika",
    2026-09-18). Unauthenticated like /project/settings: every value is
    on an Engineer dialog of the panel, none is a secret (the MQTT
    password and the API tokens never sit in this file)."""
    pm = core.project_manager
    return {"source": "controller.local.json" if pm.is_epw_project() else "project.json",
            "path": pm.settings_file if pm.is_epw_project() else None,
            "language": pm.get_language(), "settings": pm.local_settings()}


@app.get("/api/v1/counters")
def get_switching_counters(core=Depends(get_core)):
    """Every switching counter as the panel shows it (closes, opens,
    closed time, threshold). {"available": false} when the module is
    not in the composition."""
    manager = getattr(core, "switching_counters", None)
    if manager is None:
        return {"available": False, "counters": {}}
    return {"available": True, "counters": manager.get_all_snapshots()}


@app.post("/api/v1/counters/{tag_name}/reset")
def reset_switching_counter(tag_name: str, core=Depends(get_core), level: str = Depends(_require_engineer)):
    """Zeroes one counter (after a device was replaced) - the same
    SwitchingCounterManager.reset_counter() the panel's own Engineer
    context menu calls, so the threshold stays and the audit trail gets
    the same COUNTER_RESET entry with the API actor (decided 2026-09-18:
    "liczniki powinny mieć możliwość zerowania poprzez Studio lub przez
    inżyniera w runtime")."""
    manager = getattr(core, "switching_counters", None)
    if manager is None:
        raise HTTPException(status_code=404, detail="Switching counters are not in this controller's composition.")
    if tag_name not in manager.get_all_snapshots():
        raise HTTPException(status_code=404, detail=f"No switching counter for {tag_name}.")
    actor = f"API:{level}"
    old = manager.reset_counter(tag_name)
    manager.flush_to_project()
    if core.audit_logger is not None:
        core.audit_logger.record("COUNTER_RESET", actor,
                                 f"{tag_name}: switching counter reset (was {old['closes']} closes, "
                                 f"{old['opens']} opens)")
    return {"reset": True, "tag": tag_name, "previous": old, "actor": actor}


@app.post("/api/v1/project/install")
async def install_project(request: Request, expected_revision: Optional[int] = None, restart: bool = True,
                          reload: bool = True,
                          core=Depends(get_core), level: str = Depends(_require_engineer)):
    """Installs the projekt.epw in the request body as this controller's
    project (ProjectManager.install_project_file: checked by the shared
    reader first, previous file kept as .bak, rolled back at the next
    start if the new one is refused there) and puts it into service.

    By default the controller REBUILDS ITSELF from the new file without
    restarting (EPWCore.reload_project): cards, points, apparatuses,
    commands, the alarm system, the protections, the logic and the panel
    are all replaced in place. `?reload=false` installs the file and
    leaves it for the next start; `?restart=true&reload=false` is the
    old behaviour, a restart a moment after answering. A restart is
    never scheduled on top of a reload that worked - there would be
    nothing left to restart for.

    `expected_revision` is the revision Studio read from GET
    /api/v1/project before deciding to send: when the controller's
    revision differs by then (the panel saved a setting in between), the
    install is refused with 409 and the current header, so Studio looks
    again instead of overwriting blind (SPEC "Wersjonowanie": "rozjazd =
    ZATRZYMAĆ SIĘ")."""
    actor = f"API:{level}"
    pm = core.project_manager
    header = pm.get_project_header()
    current = header.get("revision")
    if expected_revision is not None and current is not None and current != expected_revision:
        if core.audit_logger is not None:
            core.audit_logger.record("API_PROJECT_INSTALL_REFUSED", actor,
                                     f"expected revision {expected_revision}, controller has {current}", success=False)
        raise HTTPException(status_code=409, detail={"error": "revision_mismatch", "expected_revision": expected_revision,
                                                     "controller": header})
    payload = await request.body()
    if not payload:
        raise HTTPException(status_code=400, detail={"error": "empty_body"})
    target_dir = os.path.dirname(os.path.abspath(pm.project_file)) or "."
    fd, temporary = tempfile.mkstemp(prefix="upload.", suffix=".epw", dir=target_dir)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(payload)
        ok, error = pm.install_project_file(temporary, actor=actor)
    finally:
        try:
            os.remove(temporary)
        except OSError:
            pass
    if not ok:
        if core.audit_logger is not None:
            core.audit_logger.record("API_PROJECT_INSTALL_REFUSED", actor, error["text"], success=False)
        raise HTTPException(status_code=400, detail={"error": "project_refused", "reason": error})
    from epw_os.core import project_format as pf
    installed = pf.read_project(pm.project_file)
    revision = installed.project.revision if installed.ok else None
    settings_hash = pf.settings_hash(installed.project) if installed.ok else None
    reloaded = None
    if reload:
        # Synchronous, inside the request: the caller (Studio) is told
        # whether the controller is actually RUNNING the project it just
        # sent, which is the only answer worth having. A refused reload
        # leaves the previous project running.
        result = core.reload_project(actor=actor, level=None)
        reloaded = {"success": result["success"], "reason": result["reason"],
                    "removed_tags": result["removed_tags"],
                    "issues": [issue["text"] for issue in result["issues"]],
                    "logic": {"success": result["logic"].get("success"),
                              "reason": result["logic"].get("reason", "")}}
    if restart and not (reloaded and reloaded["success"]):
        # Answer first, then go down: the request must complete before
        # the process exits.
        threading.Timer(1.5, core.request_restart,
                        args=(f"project installed via REST (revision {revision})", actor)).start()
        restart_scheduled = True
    else:
        restart_scheduled = False
    return {"installed": True, "path": pm.project_file, "revision": revision, "settings_hash": settings_hash,
            "previous_revision": current, "restart_scheduled": restart_scheduled,
            "reloaded": reloaded, "actor": actor}
