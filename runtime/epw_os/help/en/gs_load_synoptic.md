# Loading a Synoptic Screen (.epwsyn)

**Project → Load Synoptic Screen...** (**Engineer** only) reads a
schematic screen exported by the EPW Synoptic Editor (a `.epwsyn` file)
and shows a summary of what it contains. It does **not** draw the
screen — this is a data check, not a viewer; drawing the screen on the
Main View is a separate, later step.

After you pick a file, the summary shows:

- the project name recorded in the file,
- how many drawing objects it has,
- how many **devices** are in its device registry, broken down by the
  five device behaviors — **SWITCHED** (controllable two-state, e.g. a
  contactor or valve), **SIGNAL** (read-only signalling, e.g. a lamp or
  sensor contact), **MEASURED** (an analog reading), **MODULATED** (a
  continuously controllable device, e.g. a VFD), **SELECTOR** (a
  physical multi-position selector switch),
- any warnings.

**Why devices matter separately from objects:** in the Synoptic
Editor's format, a device's full configuration — its feedback contact,
its command output, its safe-state behavior — is never stored on the
drawing itself. A drawing object only says "at this spot, show this
symbol, and it represents device X". The device's actual configuration
lives once in the file's own device registry, no matter how many
drawing objects (or screens) point at it. The same device legitimately
appearing on more than one object is normal, not a problem.

**About warnings:** the one warning this check can produce is a
drawing object that points at a device id which isn't in the file's
registry. That object still loads — it simply has nothing to look up —
so this is shown as a warning, not treated as a reason to refuse the
file. A file is refused only for a structural problem: not an
`EPW_SYNOPTIC` file, a schema version newer than this copy of EPW OS
understands, a required field missing, or two drawing objects sharing
the same id. A file rejected for any of those reasons changes nothing —
your active project is untouched either way.

Every load (successful or refused) is recorded in the
[Audit Log](help://ea_audit_log): who, when, which file, and — for a
successful load — how many objects and devices it contained.
