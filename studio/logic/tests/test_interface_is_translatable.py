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
#
# feat/signal-register 1.6: QTreeWidgetItem, addRow and setToolTip were
# the hole this test had. The signal picker's three section headings went
# straight into QTreeWidgetItem(parent, ["Physical inputs and outputs"])
# and the "New internal signal" form labelled its six fields with
# addRow("Name", ...) - every one of them English in a Polish session,
# and every one of them invisible to a test that only compared the two
# locale files against each other. A key that is missing gets caught;
# text that never asked for a key at all does not.
_TEXT_CALLS_ANY_ARG = {
    "addTab", "addAction", "addMenu", "addItem", "setHeaderLabels",
    "QTreeWidgetItem", "addRow", "setToolTip",
}

# DELIBERATELY NOT LISTED: addItems. Its strings are almost always the
# STORED VALUES of a property ("BOOL"/"REAL", "True"/"False",
# "NO FORCE"/"FORCE TRUE"), written verbatim into .epwlogic and compared
# verbatim by the validator, the exporter and the runtime. Translating
# them would not translate an interface, it would change the file
# format - and a Polish project would then fail to open in English.
# Where a combo genuinely lists LABELS, they go through
# ui/display_names.py (enum_label), which is where that separation
# already lives.

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
            found.extend(_prose_in(arg))
    return found


def _prose_in(node):
    """Every user-visible literal inside one argument.

    Three shapes, because an argument is written three ways here: a
    plain string, an f-string (whose literal parts are what a person
    reads), and a LIST of either - QTreeWidgetItem and setHeaderLabels
    both take their text that way. The list case used to look at plain
    strings only, so a heading built as [f"Changed blocks ({n})"] passed
    a test whose whole purpose was to catch exactly that.
    """
    if isinstance(node, ast.Constant):
        return [(node.lineno, node.value)] if _is_prose(node.value) else []
    if isinstance(node, ast.JoinedStr):
        return [(part.lineno, part.value) for part in node.values
                if isinstance(part, ast.Constant) and _is_prose(part.value)]
    if isinstance(node, ast.List):
        out = []
        for element in node.elts:
            out.extend(_prose_in(element))
        return out
    return []


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
