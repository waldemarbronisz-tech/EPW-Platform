"""Studio's own version string - task "fix/project-format-integrity"
points 4.4 (splash screen) and 8.3 (version visible in the status bar/
title) both need the SAME number, so it lives in exactly one place
rather than being typed twice and drifting.

No formal release process exists yet for Studio itself (unlike EPW-OS's
own runtime/epw_os, which this module does NOT read from - GRANICE,
and the two are versioned independently anyway, one program embedding
two editors is not "the same release" as the controller OS). Bumped by
hand until/unless a real release process exists.
"""
STUDIO_VERSION = "0.1.0"
