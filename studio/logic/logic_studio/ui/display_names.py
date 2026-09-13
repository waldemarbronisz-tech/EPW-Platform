"""English display names for values that are STORED in Polish.

The interface of Logic Studio is English, but a few property keys and
enum values were written into project files (and into the export EPW-OS
reads) in Polish long before that - "Sygnał", "Minimalny poziom dostępu",
"Własny", "Brak", ... Renaming them in the data would break every existing
.epwlogic file and every export already deployed, for no gain to the
person using the editor. So the data keeps its values, and this module is
the one place that says what to SHOW for them.

Rule for callers: display with property_label()/enum_label(); always store
the original value (keep it as the combo item's data, never its text).
"""

PROPERTY_LABELS = {
    "Sygnał": "Signal",
    "Minimalny poziom dostępu": "Minimum access level",
    # doc.text/doc.note/doc.section "Rozmiar tekstu (pkt)" - the grid shows
    # the key without its unit suffix, so the bare name is what is looked up.
    "Rozmiar tekstu": "Text size",
}

# Unit suffixes shown on numeric editors. The stored key keeps "(pkt)".
UNIT_LABELS = {
    "pkt": "pt",
}


def unit_label(unit):
    """What to show for a unit parsed out of a stored property key."""
    return UNIT_LABELS.get(unit, unit)

ENUM_LABELS = {
    # analog.deadband "Mode"
    "Bezwzględny": "Absolute",
    "Procentowy": "Percentage",
    # system.button "Mode"
    "Monostabilny": "Momentary",
    "Bistabilny": "Toggle",
    # analog.quality "Range Source"
    "Z punktu analogowego": "From analog point",
    "Własny": "Custom",
    # input.ai "Hold Timeout Value"
    "Zero": "Zero",
    "Ostatnia dobra": "Last good",
    "Dolna granica zakresu": "Range minimum",
    # system.signal_out "Minimalny poziom dostępu"
    "Brak": "None",
}


def property_label(key):
    """What to show for a property key. Unknown keys are shown as they are."""
    return PROPERTY_LABELS.get(key, key)


def enum_label(value):
    """What to show for a stored enum value. Unknown values are shown as they are."""
    return ENUM_LABELS.get(value, value)
