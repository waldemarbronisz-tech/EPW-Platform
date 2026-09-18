# Protection Tests

The "internal Omicron": a protection test is a forced state, a measured
response time and a report - on the same mechanism as forcing in the
point registry. The **controller** runs the test, not Studio: Studio
starts it, follows it and shows the reports the controller keeps
(`protection_test_reports.json`).

**Process protection.** The controller forces the analog point past the
upper threshold, measures the time until the trip
(`Process.<id>.Exceeded`) and compares it with the configured delay: a
trip before the delay, or clearly after it, is a FAIL. It then forces
the value back inside the band and measures the reset time; finally it
releases the force. A disabled or already tripped protection is not
tested (BLOCKED).

**Apparatus.** The controller issues the command that changes the state
(OPEN when the feedback reads closed, otherwise CLOSE) down the same
path as from the panel - with logic interlocks and safety checks, so a
refused command is BLOCKED, not bypassed. It measures the time until
the feedback follows, then restores the state with the opposite command
and measures that too.

**Rules.** Engineer token; one test at a time; the start, the result and
every force are audited (`PROTECTION_TEST_*`, `FORCE_*`). The
protection path - breakers, apparatuses designated Q, anything that is
not a project point - is never forced, so never tested this way. ADA01's
electrical protection stages are checked at the cabinet with the panel's
verifier (a measurement ramp), not from here.

**Reports.** The table shows the settings, the measurement (trip, reset,
feedback times) and the reason for the result; double-click opens the
timed steps. "Save Reports as CSV" writes every report the controller
holds to a file - evidence for the commissioning record.
