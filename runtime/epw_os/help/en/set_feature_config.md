# Feature Configuration

**Settings → Feature Configuration...** (Engineer level) turns
individual controller functions on and off, project by project. A
switch cabinet needs Protection Settings; a house doesn't. A garden
shed needs the Intrusion Alarm System; a substation cabinet doesn't.

**Turning a function off STOPS it — this is not the same as hiding a
page.** An off function:
- runs no background thread and starts no timer
- registers no tags in TagManager at all
- writes nothing to disk
- disappears from the navigation tree entirely

This matters most on the intended target platform, an Orange Pi
running from an SD card — every module that doesn't need to run is one
less thread, one less block of memory, and one less thing writing to
the card.

**What can't be turned off**: Main View (there'd be nothing left to use
the program for), Digital Inputs and Control Outputs (the controller's
own core job), Alarms and the Event Recorder (basic diagnostics), and
the Audit Log — always, without exception, since an audit trail that
could be switched off would itself become a way to hide what was done
while it was off.

**Turning a function back on** starts its module fresh and restores
its tags immediately - no restart either way, the window briefly
rebuilds itself in place, the same mechanism a language switch already
uses.

**Before turning something off**, you're warned if your logic program
references any of its tags, or if it produces data (alarm history,
switching counters, service notes...) that will simply stop being
recorded — turning it off anyway is still possible, but only after
that warning, explicitly confirmed.

**Nothing already recorded is ever deleted.** Alarm history, switching
counters, service notes - all of it stays exactly where it was. Turn
the function back on later and it's all still there, with an honest
gap for the time it was off, not a rewritten history pretending nothing
happened.

**Engineer Mode needs Protection Settings (Electrical)** — Engineer
Mode's whole purpose is verifying the protection settings actually
configured for this project; with Electrical protections off there's
nothing real to verify, so Engineer Mode is unavailable until it's
back on, regardless of its own switch.

**Event History and Configuration (System Alarmowy) need the Intrusion
Alarm System itself** — both view/edit the same live intrusion data,
so they're unavailable whenever the whole Intrusion Alarm System is
off, regardless of their own switch (the same dependency Engineer Mode
has on Protection Settings above). Overview does NOT have this
dependency separately — it reuses the Intrusion Alarm System's own
switch directly, since it's the same page that switch always
controlled.

**Process Protections is fully independent of Protection Settings
(Electrical)** — a different module entirely (its own analog-threshold
watchdogs, not the classic relay-style settings Electrical/Engineer
Mode share), so it stays available even with Electrical off, and vice
versa.

The configuration is saved in the project file itself, not the
program - moving the project to another machine takes its feature
configuration with it. An existing project that predates this screen
entirely behaves exactly as it always has: every function on.
