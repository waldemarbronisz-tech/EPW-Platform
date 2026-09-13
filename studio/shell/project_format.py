"""Thin re-export of shared/project_format.py - the ONE implementation of
the `projekt.epw` format, read by both Studio and runtime (task "runtime
czyta projekt.epw", point 1.1).

The module used to live here. Runtime now reads the same file, so a copy
on each side would be exactly the kind of parallel implementation that
drifts apart (the addressing grammar went through that once already -
see shared/addressing.py). Studio imports it the normal way (the repo
root is on Studio's sys.path); runtime loads it by path, see
runtime/epw_os/core/project_format.py.

Every name - including the underscore helpers Studio's own tests reach
for - is copied from the shared module, so `studio.shell.project_format.X`
and `shared.project_format.X` are the same object.
"""
import shared.project_format as _shared

globals().update({name: value for name, value in vars(_shared).items() if not name.startswith("__")})
