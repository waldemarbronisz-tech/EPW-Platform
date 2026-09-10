"""Task "strażnik serializacji — generyczny" (branch fix/project-format-
integrity, point 1). Every hand-written round-trip test in
test_project_format.py enumerates fields BY HAND (`Card(id=..., model=
..., kind=..., channels=...)`) - a field added to a dataclass without
being added to _to_json_dict()/load_project()'s own (partly manual,
see Device below) reconstruction passes every one of those tests
silently, because the test itself never looks at the field either.
This is the "same bug class 8 times" the task cites.

This module never lists a field by name for any dataclass. It walks
dataclasses.fields() of every project_format.py dataclass, builds an
instance with EVERY field set to a value different from that field's
own default (_fill_dataclass()), round-trips the whole Project through
save_project()/load_project(), and compares every field of every
nested structure back against what was set - by walking fields() again
(_diff_dataclass()), never by naming one.

The only per-field knowledge in this file is the small, explicitly-
justified _SAVE_MUTATES set: four fields save_project()/load_project()
documents as INTENTIONALLY not surviving unchanged (revision bumps,
modified_by/modified_at get overwritten, is_dirty always clears) - see
that function's own docstring. Skipping those four is not "silently
loosening the check" - each has its own assertion below, checking the
DOCUMENTED transformation instead of identity.
"""
import dataclasses
import typing

import pytest

from studio.shell.project_format import (
    Card,
    Device,
    ElectricalProtectionStage,
    Line,
    Location,
    ModbusBusConfig,
    Point,
    PowerSupervision,
    ProcessProtection,
    Project,
    ProjectMetadata,
    Zone,
    load_project,
    new_project,
    save_project,
)

# The four (class, field) pairs save_project()/load_project() documents
# as deliberately NOT round-tripping unchanged - see project_format.py's
# own save_project() docstring ("Bumps revision and modified_at/
# modified_by ... clears is_dirty"). Verified below by their own
# assertions, not skipped silently.
_SAVE_MUTATES = {
    (Project, "revision"),
    (Project, "modified_by"),
    (Project, "is_dirty"),
    (ProjectMetadata, "modified_at"),
}

_counter = iter(range(10_000_000))


def _next_marker() -> int:
    return 900_000_000 + next(_counter)


def _unwrap_optional(py_type):
    """Optional[X] is typing.Union[X, None] at runtime - returns X, or
    py_type unchanged if it isn't an Optional at all."""
    if typing.get_origin(py_type) is typing.Union:
        args = [a for a in typing.get_args(py_type) if a is not type(None)]
        if len(args) == 1:
            return args[0]
    return py_type


def _scalar_marker(py_type, field_default):
    """A value of `py_type`, guaranteed different from `field_default`
    (relevant for bool, where only two values exist at all)."""
    py_type = _unwrap_optional(py_type)
    if py_type is bool:
        return not bool(field_default) if isinstance(field_default, bool) else True
    if py_type is int:
        return _next_marker()
    if py_type is float:
        return float(_next_marker()) + 0.25
    if py_type is str:
        return f"ZZZ_MARKER_{_next_marker()}"
    raise TypeError(f"test doesn't know how to build a marker {py_type!r} value")


def _default_for(f: dataclasses.Field):
    if f.default is not dataclasses.MISSING:
        return f.default
    if f.default_factory is not dataclasses.MISSING:  # type: ignore[misc]
        return f.default_factory()
    return dataclasses.MISSING  # a required field - nothing to differ from


def _fill_dataclass(cls, path: str):
    """Builds a `cls` instance with EVERY field set to something other
    than its own default - list[<nested dataclass>] fields get one
    fully-filled nested instance (recursive), list[str] fields get one
    marker string, dict fields get one marker entry, nested-dataclass
    fields get a fully-filled nested instance, everything else goes
    through _scalar_marker(). Never references a field by name."""
    kwargs = {}
    for f in dataclasses.fields(cls):
        field_path = f"{path}.{f.name}"
        origin = typing.get_origin(f.type)
        if f.type is list or origin is list:
            (elem_type,) = typing.get_args(f.type) or (str,)
            if dataclasses.is_dataclass(elem_type):
                kwargs[f.name] = [_fill_dataclass(elem_type, field_path)]
            else:
                kwargs[f.name] = [_scalar_marker(elem_type, None)]
        elif f.type is dict or origin is dict:
            kwargs[f.name] = {"zzz_marker_key": [1.5, 2.5]}
        elif dataclasses.is_dataclass(f.type):
            kwargs[f.name] = _fill_dataclass(f.type, field_path)
        else:
            kwargs[f.name] = _scalar_marker(f.type, _default_for(f))
    return cls(**kwargs)


def _diff_dataclass(cls, expected, actual, path: str, mismatches: list):
    for f in dataclasses.fields(cls):
        field_path = f"{path}.{f.name}"
        if (cls, f.name) in _SAVE_MUTATES:
            continue  # asserted separately, see test_save_documented_mutations_below
        exp_val = getattr(expected, f.name)
        act_val = getattr(actual, f.name)
        origin = typing.get_origin(f.type)
        if (f.type is list or origin is list) and exp_val and dataclasses.is_dataclass(type(exp_val[0])):
            if len(exp_val) != len(act_val):
                mismatches.append(f"{field_path} (list length: {len(exp_val)} -> {len(act_val)})")
                continue
            for i, (e, a) in enumerate(zip(exp_val, act_val)):
                _diff_dataclass(type(e), e, a, f"{field_path}[{i}]", mismatches)
        elif dataclasses.is_dataclass(f.type):
            _diff_dataclass(f.type, exp_val, act_val, field_path, mismatches)
        else:
            if exp_val != act_val:
                mismatches.append(f"{field_path} ({exp_val!r} -> {act_val!r})")


def test_every_dataclass_field_survives_a_save_load_round_trip(tmp_path):
    """THE guard: fills a Project (and one fully-filled instance of
    every nested dataclass this format has) with marker values, saves,
    reloads, and asserts every field matches - by walking fields(), so
    a field added to ANY of these dataclasses without also being wired
    into serialization fails THIS test with that field's own dotted
    path, without anyone having named it here first."""
    filled = _fill_dataclass(Project, "Project")
    # metadata.name is the one field new_project()-shaped callers always
    # expect to be a real string - _fill_dataclass() already gave it a
    # marker string like every other str field, nothing special needed.

    path = tmp_path / "projekt.epw"
    save_project(filled, path)
    loaded = load_project(path)

    mismatches: list = []
    _diff_dataclass(Project, filled, loaded, "Project", mismatches)
    assert not mismatches, (
        "Field(s) did not survive save_project()/load_project() unchanged - "
        "wire them into _to_json_dict()/load_project():\n  " + "\n  ".join(mismatches)
    )


def test_save_documented_mutations_are_exactly_the_four_expected():
    """The flip side of skipping _SAVE_MUTATES above in the generic
    diff - proves those four fields DO change, in EXACTLY the
    documented way, so excluding them from the generic check isn't
    quietly hiding a real regression in them either."""
    import time

    p = new_project("Test")
    p.revision = 41
    p.modified_by = "panel"
    p.metadata.modified_at = "2000-01-01T00:00:00+00:00"
    p.is_dirty = False  # new_project() sets True; save_project() must clear it regardless

    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "p.epw"
        before = time.time()
        save_project(p, path)
        after = time.time()

        assert p.revision == 42, "save_project() must bump revision by exactly 1"
        assert p.modified_by == "studio", "save_project() must always attribute the save to 'studio'"
        assert p.is_dirty is False, "save_project() must always clear is_dirty"

        loaded = load_project(path)
        assert loaded.revision == 42
        assert loaded.modified_by == "studio"
        assert loaded.is_dirty is False
        modified_at_epoch = _iso_to_epoch(loaded.metadata.modified_at)
        assert before - 1 <= modified_at_epoch <= after + 1, "modified_at must be refreshed to ~now on save"


def _iso_to_epoch(iso_string: str) -> float:
    from datetime import datetime
    return datetime.fromisoformat(iso_string).timestamp()


# -- the task's own required proof, automated: temporarily add an
# unwired field to a copy of Card's shape and confirm the generic guard
# names it - kept as a real, always-running test (not a one-off manual
# demo) so this guard is proven to actually fire, not just asserted to.

def test_guard_actually_fails_naming_an_unwired_field():
    """Reproduces the exact failure the task asked to demonstrate,
    without touching the real Card dataclass: a throwaway dataclass
    shaped exactly like _to_json_dict()'s OWN Device-serialization
    pattern (manual dict construction, easy to forget a field in) - one
    field present on the class but absent from a hand-written
    save/load pair. Asserts the mismatch message names that exact
    field, proving the guard mechanism (not just this test file) does
    what it claims."""
    @dataclasses.dataclass
    class _Forgetful:
        id: str
        remembered: str = "x"
        forgotten: str = "y"  # present on the class, absent below on purpose

    def _save(obj):
        return {"id": obj.id, "remembered": obj.remembered}  # "forgotten" NOT included

    def _load(data):
        return _Forgetful(id=data["id"], remembered=data["remembered"])  # defaults "forgotten"

    filled = _fill_dataclass(_Forgetful, "_Forgetful")
    reloaded = _load(_save(filled))

    mismatches: list = []
    _diff_dataclass(_Forgetful, filled, reloaded, "_Forgetful", mismatches)
    assert len(mismatches) == 1
    assert mismatches[0].startswith("_Forgetful.forgotten "), (
        f"expected the guard to name the forgotten field, got: {mismatches}"
    )
