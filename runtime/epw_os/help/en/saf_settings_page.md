# The Settings Page

The **Protection Settings** page shows a tree of protection functions
grouped into categories, each containing individual stages. For each
stage: an enable/disable field, measurement source, setting, hysteresis,
time delay, action, current status, current measured value, and
statistics (number of pickups, trips, operating time).

Status colors: green (READY), yellow (PICKUP), red (TRIP), blue
(BLOCKED), gray (DISABLED).

Editing any setting, enabling/disabling a stage, and resetting
statistics all require the **Engineer** level — with no exception (even
in simulation mode). Changing a setting shows an additional confirmation
window before it's saved.

A separate **Engineer Mode** page lets an Engineer run a formal
verification test of a chosen protection stage and records the result
as a report — see [Engineer Mode (Protection Verification)](help://saf_engineer_mode).
