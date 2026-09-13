"""Small JSON files the controller keeps for itself - runtime_state.json
and controller.local.json (task "runtime czyta projekt.epw", etap 2).

Headless, standard library only. Two operations, both written for a
device that can lose power at any moment:

- atomic_write_json(): the new content goes to a temporary file in the
  same directory, is flushed and fsync'ed, and replaces the old file in
  one os.replace(). A power cut leaves either the old file or the new
  one on disk, never half of each - the arming state is written this way
  on EVERY change (SPEC_PROJEKT_EPW.md: "zapis stanu uzbrojenia musi być
  natychmiastowy przy każdej zmianie"), so a torn write is a real case,
  not a theoretical one.
- read_json_object(): never raises. Returns the dict, or None together
  with what went wrong ("missing" / "corrupt") so the caller can decide
  how loud to be about it.
"""
import json
import os
import tempfile
from pathlib import Path


def atomic_write_json(path, data) -> None:
    """Raises OSError when the file cannot be written - the caller logs
    it; losing a write silently is exactly what this module exists to
    prevent."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True).encode("utf-8")
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
    _fsync_directory(path.parent)


def _fsync_directory(directory: Path) -> None:
    """On POSIX the rename itself is only durable once the directory
    entry is flushed too. Not available (and not needed) on Windows."""
    if os.name != "posix":
        return
    try:
        fd = os.open(str(directory), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def read_json_object(path):
    """(dict, None) on success; (None, "missing") when there is no file;
    (None, "corrupt") when it exists but is not a JSON object."""
    path = Path(path)
    if not path.exists():
        return None, "missing"
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, UnicodeDecodeError, ValueError):
        return None, "corrupt"
    if not isinstance(data, dict):
        return None, "corrupt"
    return data, None
