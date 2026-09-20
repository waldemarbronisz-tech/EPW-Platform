"""No interface text hardcoded in Logic Studio's source.

Owner's instruction: "jeżeli polski to wszędzie ma być polski". The
hard part is not translating what is there today - it is that the next
panel somebody writes will have `QPushButton("Add")` in it, ship, and be
English for ever inside an otherwise Polish application. Nothing fails,
nothing warns; you only find out by looking.

So this walks the source with `ast` and fails on a user-visible string
literal that never went through tr(). It is deliberately narrow: only
the calls whose argument IS what a person reads.
"""
import ast
import re
import sys
from pathlib import Path

import pytest

_UI_ROOT = Path(__file__).resolve().parents[1] / "logic_studio"
if str(_UI_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(_UI_ROOT.parent))

from logic_studio import i18n

# Calls whose (first) string argument is read by a person.
_TEXT_CALLS = {
    "setWindowTitle", "setPlaceholderText", "setStatusTip",
    "QPushButton", "QLabel", "QGroupBox", "QCheckBox", "QRadioButton",
}
# Calls where a person reads an argument that is not the first one.
_TEXT_CALLS_ANY_ARG = {"addTab", "addAction", "addMenu", "addItem", "setHeaderLabels"}

# Strings that are not prose: symbols, separators, format scaffolding,
# and the handful of technical tokens that are the same in every
# language. Kept explicit - an exception nobody can see is how the
# English crept back in the first place.
_NOT_PROSE = {
    "", " ", "-", "--", "---", "...", "*", "|", "/", "\\", ":", ".", ",",
    "0", "1", "OK", "J", "L", "C", "R",
}


_MARKUP = re.compile(r"&\w+;|<[^>]*>")


def _is_prose(value):
    if not isinstance(value, str):
        return False
    if value.strip() in _NOT_PROSE:
        return False
    if not any(ch.isalpha() for ch in value):
        return False
    # Markup around a translated value, not text in its own right:
    # "<b>", "</b><br>", "</b> - <b>". A label built as
    # "<b>" + tr(...) + "</b>" is correctly translated; what is left
    # once the tags and entities are removed has to contain a letter
    # before this counts as something a person reads.
    if not any(ch.isalpha() for ch in _MARKUP.sub("", value)):
        return False
    # An identifier-looking token ("macro.pins_button", "DI", "epwlogic")
    # is a key or a technical name, not a sentence.
    if len(value) <= 3 and value.isupper():
        return False
    return True


def _offending_strings(path):
    """[(line, text)] for every user-visible literal in `path` that is
    not a tr() call."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = (node.func.attr if isinstance(node.func, ast.Attribute)
                else node.func.id if isinstance(node.func, ast.Name) else None)
        if name is None:
            continue
        if name in _TEXT_CALLS:
            args = node.args[:1]
        elif name in _TEXT_CALLS_ANY_ARG:
            args = node.args
        else:
            continue
        for arg in args:
            if isinstance(arg, ast.Constant) and _is_prose(arg.value):
                found.append((arg.lineno, arg.value))
            elif isinstance(arg, ast.List):
                for element in arg.elts:
                    if isinstance(element, ast.Constant) and _is_prose(element.value):
                        found.append((element.lineno, element.value))
            elif isinstance(arg, ast.JoinedStr):
                # An f-string built from prose - "Trend — {x}" and the
                # like. The literal parts are what a person reads.
                for part in arg.values:
                    if isinstance(part, ast.Constant) and _is_prose(part.value):
                        found.append((part.lineno, part.value))
    return found


UI_FILES = sorted((_UI_ROOT / "ui").rglob("*.py"))


def test_there_are_ui_files_to_check():
    assert len(UI_FILES) > 15, "the walk found nothing - the path is wrong"


@pytest.mark.parametrize("path", UI_FILES, ids=lambda p: p.name)
def test_no_hardcoded_interface_text(path):
    offending = _offending_strings(path)
    assert not offending, (
        f"{path.name}: interface text that never goes through tr():\n" +
        "\n".join(f"  line {line}: {text!r}" for line, text in offending))


# --- and the other half: the catalogues agree with each other ---------------

def _flatten(data, prefix=""):
    out = {}
    for key, value in data.items():
        full = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            out.update(_flatten(value, full))
        else:
            out[full] = value
    return out


def test_both_languages_carry_exactly_the_same_keys():
    english = _flatten(i18n._load("en"))
    polish = _flatten(i18n._load("pl"))
    only_en = sorted(set(english) - set(polish))
    only_pl = sorted(set(polish) - set(english))
    assert not only_en, f"missing from pl.json: {only_en}"
    assert not only_pl, f"only in pl.json: {only_pl}"


def test_every_placeholder_survives_translation():
    """A translation that drops a {name} shows a literal brace to the
    operator, or throws where the code formats it."""
    english = _flatten(i18n._load("en"))
    polish = _flatten(i18n._load("pl"))
    placeholders = re.compile(r"\{(\w+)\}")
    for key, text in english.items():
        assert set(placeholders.findall(text)) == set(placeholders.findall(polish[key])), \
            f"{key}: placeholders differ between languages"


def test_nothing_in_the_english_catalogue_is_actually_polish():
    polish_letters = set("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ")
    for key, text in _flatten(i18n._load("en")).items():
        assert not (set(text) & polish_letters), f"en.json/{key} is Polish: {text!r}"
