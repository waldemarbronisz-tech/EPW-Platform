# Protection Tests

The internal Omicron: the controller forces a state itself, measures the
response time and keeps a report. No test set, and no taking the
installation apart.

It needs an Engineer token; every test is audited, and the reports stay
**on the controller**.

## What can be tested

**A process protection** — its analog point is forced past the
threshold, the trip is timed against the configured delay, then the
value goes back in band and the reset is timed.

**An apparatus** — the command goes **down the same path as from the
panel**: logic interlocks, the safety kernel, training mode and forces
all apply unchanged. The feedback is timed, then the state is restored.

The **What can be tested** list shows the kind, id, name, settings and
state: `ready`, `disabled`, `tripped — clear it first`.

## What this test does not cover

**The electrical protection path (ADA01).** The card executes the ANSI
functions, not the controller's program — that cannot be checked by
forcing a tag.

## Reports

A table: started, kind, subject, result, settings, **measured**, reason.
Double-click opens one test's steps — what it did, in order, and what it
measured.

**Save Reports as CSV** exports them to a file, for the commissioning
documentation.

An older EPW-OS without this feature is recognised and says so.
