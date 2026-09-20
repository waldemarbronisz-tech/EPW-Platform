"""feat/help-system §3.3/§7.5 — the keyboard-shortcut table shown in
help, generated from the ACTUAL `self._make_action(...)` call sites in
ui/main_window.py via `ast`, not hand-transcribed. A shortcut changed in
the code is read straight from the file every time this is called, so
it can never drift from what's really registered — the same "generated,
not hand-maintained" principle as core/block_catalog.py, and for the
identical reason (REPORT.md/AUDIT_REPORT.md's own documented history of
hand-written documentation silently disagreeing with the code).

Deliberately reads the SOURCE FILE with `ast`, rather than introspecting
live QAction objects on a running MainWindow instance: this stays
headless (no PySide6 import, no QApplication needed — testable exactly
like block_catalog.py) and catches every `_make_action()` call
unconditionally, not just the ones a particular code path happened to
execute during a test run.
"""
import ast
from pathlib import Path

_MAIN_WINDOW_PATH = Path(__file__).resolve().parent.parent / "ui" / "main_window.py"


def _string_value(node):
    """A plain ast.Constant string, or None for anything else (a
    variable, an f-string, ...) -- shortcuts in this codebase are
    always written as literal strings, so anything else is simply not
    a shortcut worth listing."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _label_value(node):
    """An action's LABEL, which since the interface became bilingual is
    written as `tr("menu.save")` rather than as "Save".

    The KEY is what this returns, not the text: resolving it here would
    freeze one language into the extracted table, and the table is built
    fresh every time the help topic is opened - in whatever language is
    active then. `_label_text()` below does the resolving, at that
    point."""
    literal = _string_value(node)
    if literal is not None:
        return literal
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == "tr" and node.args):
        return _string_value(node.args[0])
    return None


def _label_text(label):
    """A key resolved in the active language; anything else unchanged.
    Imported inside the function so this module stays importable, and
    testable, without the rest of Logic Studio."""
    from logic_studio.i18n import tr
    return tr(label)


def _extract_make_action_call(call: ast.Call):
    """Returns (text, shortcut) or None if this isn't a recognizable
    `self._make_action(text, slot, shortcut, ...)` call, or it has no
    shortcut at all."""
    func = call.func
    if not (isinstance(func, ast.Attribute) and func.attr == "_make_action"):
        return None
    if not call.args:
        return None
    text = _label_value(call.args[0])
    if text is None:
        return None

    shortcut = None
    if len(call.args) >= 3:
        shortcut = _string_value(call.args[2])
    for kw in call.keywords:
        if kw.arg == "shortcut":
            shortcut = _string_value(kw.value)

    if not shortcut:
        return None
    return text, shortcut


def extract_shortcuts(source_path=None) -> list:
    """[(text, shortcut), ...] in source order, from every
    `self._make_action(...)` call in ui/main_window.py that has a
    non-empty shortcut. `source_path` is overridable for tests."""
    path = Path(source_path) if source_path else _MAIN_WINDOW_PATH
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    results = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            found = _extract_make_action_call(node)
            if found is not None:
                results.append(found)
    return results


def shortcuts_markdown() -> str:
    """§3.3: the actual help TOPIC content — a table, generated fresh
    every time this is called, in the language active at that moment."""
    from logic_studio.i18n import tr

    rows = extract_shortcuts()
    lines = ["# " + tr("shortcuts.heading"), ""]
    if not rows:
        lines.append("*(" + tr("shortcuts.none") + ")*")
        return "\n".join(lines) + "\n"
    lines.append("| " + tr("shortcuts.col_command") + " | " + tr("shortcuts.col_shortcut") + " |")
    lines.append("|---|---|")
    for label, shortcut in rows:
        lines.append("| " + _label_text(label) + " | `" + shortcut + "` |")
    lines.append("")
    lines.append(tr("shortcuts.f1_note"))
    return "\n".join(lines) + "\n"
