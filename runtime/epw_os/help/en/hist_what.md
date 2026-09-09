# What Historian Records

Historian is a background service that records **every value change of
every tag** (inputs, outputs, analog points) to the database, with a
timestamp and data quality. Recording happens asynchronously — it does
not slow down control or visualization.

**Technical note for the curious**: the database also has a table for
alarm history, and Historian listens for the event that would populate
it — but in the current version of the program, nothing actually
generates that event, so alarm history (unlike tag value history) is
not being recorded in practice today. Active alarms are still visible
live on the Alarms page (see [Where Alarms Come From](help://alm_source))
— they simply aren't being written to Historian.

Data recorded by Historian is accessible two ways: through export (see
[Exporting Historical Data](help://hist_export)), or on screen without
exporting anything, on the [Trends page](help://trends_page).

**Simulated values**: a handful of tags (the Main View measurement
panel's voltage/current/frequency, and the Power Quality page's
sliders) have no physical sensor behind them - see
[The Measurement Panel](help://mv_measurements). Historian still
records them (so exports and trends stay complete), but with quality
**SIMULATED** instead of GOOD, so they're always distinguishable from a
real reading in an export's Quality column.

**Write deadband**: not every single value change is written. A
REAL/INT tag is only recorded once it has changed by more than a
threshold (a sensible default, adjustable per-tag in the project file),
with a periodic forced write so a perfectly stable value doesn't leave
a gap in its history either. Boolean and text tags (relay states,
statuses) are always recorded on every change — this deadband exists to
protect the storage medium (an SD card on the target hardware has
limited write endurance) from a high-frequency, near-constant analog
value, not to thin out anything where every change matters.
