"""Turns EPWCore.startup_issues into text for the operator (task "runtime
czyta projekt.epw"). Each issue carries a translation key and its
parameters; a refused project file additionally carries the shared
reader's own reason (detail_key/detail_params, "project_format.*"), and a
composition issue names its module by feature id - shown here by the
module's own display name, the same one the Feature Configuration dialog
and the navigation tree use."""
from epw_os.gui.widgets.feature_config_dialog import FEATURE_LABEL_KEYS
from epw_os.i18n import tr


def format_startup_issue(issue: dict) -> str:
    params = dict(issue.get("params", {}))
    if "module" in params:
        params["module"] = tr(FEATURE_LABEL_KEYS.get(params["module"], params["module"]), params["module"])
    text = tr(issue["key"], issue.get("text", issue["key"]), **params)
    if issue.get("detail_key"):
        text += " " + tr(issue["detail_key"], "", **issue.get("detail_params", {}))
    return text
