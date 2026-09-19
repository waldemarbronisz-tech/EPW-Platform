"""The "macro.<def_id>" type_id convention, on its own.

A macro DEFINITION (its blocks, wires and parameters) is editor data
living in the project's settings - core/macros.py in Logic Studio owns
all of it. But the type_id SPELLING is not: blocks/registry.py has to
recognize "macro.xyz" to resolve it to MacroInstanceBlock (which already
lives here in shared/, alongside every other block class), and
blocks/registry.py is imported by EPW-OS, which has no Logic Studio on
its path at all.

So the two-line string convention moved here and core/macros.py
re-exports it, rather than the shared block library importing the editor
to find out what a type_id starts with.
"""

MACRO_TYPE_PREFIX = "macro."


def macro_def_id(type_id: str):
    """None if `type_id` doesn't name a macro instance; else the
    definition id it references (the part after "macro.")."""
    if not type_id or not type_id.startswith(MACRO_TYPE_PREFIX):
        return None
    def_id = type_id[len(MACRO_TYPE_PREFIX):]
    return def_id or None  # bare "macro." (an unconfigured/corrupt instance) has no real def_id
