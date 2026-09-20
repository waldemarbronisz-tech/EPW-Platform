"""Studio's own version string - task "fix/project-format-integrity"
points 4.4 (splash screen) and 8.3 (version visible in the status bar/
title) both need the SAME number, so it lives in exactly one place
rather than being typed twice and drifting.

Versioned independently of EPW-OS on purpose - one program embedding
two editors is not "the same release" as the controller OS, and this
module deliberately does NOT read runtime/epw_os/version.py. They reach
1.0 together because the platform does, not because they share a
number. Bumped by hand; there is no release process to do it.
"""
STUDIO_VERSION = "1.0.0"
