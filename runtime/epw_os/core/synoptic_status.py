"""RT.SYNOPTIC.* - whether the screens embedded in the project are
something the panel can show.

Headless: the same reader the panel's Synoptic page uses
(epwsyn_loader) is run over every screen of the document at project load
and reload, and the verdict is kept as three facts:

  READY          - there is a screens document and every screen loads;
  FAIL           - there is a screens document and at least one screen is
                   refused by the reader (a damaged file: the panel shows
                   its "why" page instead of a drawing);
  BINDING_FAULT  - a screen loads but refers to an apparatus the project
                   does not have (an object whose deviceId resolves to
                   nothing) - the drawing shows, that symbol is dead.

No document at all is none of the three: nothing to show is not a
failure of the screens. The details (which screen, which object) are
kept for the log and the startup issues.
"""
from epw_os.core.epwsyn_loader import load_epwsyn_data
from epw_os.core.screen_set import screen_document, screen_list


def evaluate_screens(document, apparatus_ids=None) -> dict:
    """{"present", "ready", "fail", "binding_fault", "problems": [..]}."""
    status = {"present": False, "ready": False, "fail": False, "binding_fault": False, "problems": []}
    if not isinstance(document, dict) or not document:
        return status
    status["present"] = True
    known = set(apparatus_ids) if apparatus_ids is not None else None
    screens = screen_list(document) or [{"id": "", "name": ""}]
    for entry in screens:
        result = load_epwsyn_data(screen_document(document, entry["id"]))
        label = entry.get("name") or entry.get("id") or "screen"
        if not result.ok:
            status["fail"] = True
            status["problems"].append(f"{label}: {result.error}")
            continue
        for warning in result.warnings:
            if "unknown device" in warning:
                status["binding_fault"] = True
                status["problems"].append(f"{label}: {warning}")
        if known is not None:
            for obj in result.project.objects:
                device_id = obj.get("deviceId")
                if device_id and device_id not in known:
                    status["binding_fault"] = True
                    problem = f"{label}: object '{obj.get('id')}' is bound to '{device_id}', which the project has no apparatus for."
                    if problem not in status["problems"]:
                        status["problems"].append(problem)
    status["ready"] = not status["fail"]
    return status
