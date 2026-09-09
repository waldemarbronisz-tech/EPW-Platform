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

from fastapi import FastAPI, Depends, HTTPException, Request, Header
from pydantic import BaseModel
import logging

from epw_os.core.access_manager import AccessLevel

app = FastAPI(title="EPW OS API")
logger = logging.getLogger("API")


# Models
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
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    level = core.api_auth.resolve_level(token)
    if not core.api_auth.has_access(level, AccessLevel.OPERATOR):
        actor = f"API:{level}" if level else "API (no/invalid token)"
        if core.audit_logger is not None:
            core.audit_logger.record(
                "API_AUTH_FAILED", actor,
                "POST /api/v1/commands requires Operator level or higher", success=False,
            )
        raise HTTPException(
            status_code=401,
            detail="Valid Operator (or higher) API token required (Authorization: Bearer <token>)",
        )
    return level


@app.get("/api/v1/health")
def get_health(core=Depends(get_core)):
    """Returns the subsystem health states."""
    return {
        "status": "UP" if core.is_running else "DOWN",
        "subsystems": core.health_manager.get_health(),
    }


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
