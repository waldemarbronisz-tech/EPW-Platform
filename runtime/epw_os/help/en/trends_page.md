# The Trends Page

Historian has recorded every tag's value history since day one, but
until this page existed, the only way to see it was exporting to CSV
and opening it elsewhere. Trends lets you look at a value's history — or
watch it update live — without leaving the program. Available at every
access level: it's a view, not a control.

## Two modes

**History** — pick a From/To date-and-time range and click **Load**.
The pickers show your computer's local time; Historian stores time in
UTC internally, and the conversion happens automatically (the same
conversion the Historical Data export dialog already uses).

**Live** — a moving time window (1 min / 5 min / 15 min / 1 h) that
keeps scrolling forward, with new points added as they arrive. No date
range to set.

## Picking tags

Check up to **5 tags** at once from the list on the left (every tag
Historian has ever recorded anything for). Five, because that's exactly
how many colors the program's theme system guarantees are visually
distinct from each other *in every one of the five visual themes* — a
6th trace would need a color with no such guarantee.

## Axes

Tags with different engineering units get separate vertical axes
automatically — plotting a voltage and a current on the same axis would
squash the current into a flat line near zero. Up to **4 axes** at
once (with a 5-tag limit, that covers every realistic case without
crowding the chart). A boolean tag (a digital input/output) always gets
its own kind of axis, fixed to 0/1, drawn as a step — the signal
actually changes state instantly, not gradually, so the line doesn't
slope between values.

## Reading the chart

- **Scroll wheel**: zoom in/out, centered on the cursor.
- **Click and drag**: pan sideways along the time axis.
- **Hover**: a crosshair shows the time and every visible trace's value
  at that point.
- **Reset View**: back to the full loaded range (History) or the full
  current window (Live).
- The vertical scale on each axis automatically fits whatever is
  currently visible — zoom in on a flat-looking stretch and the scale
  rescales to show the real detail in it.

## Simulated data

A trace for a tag with no real sensor/meter behind it (see
[What Historian Records](help://hist_what)) is drawn **dashed**, with
"(simulated)" in the legend — the same SIMULATED marking used
everywhere else in the program, not a separate convention for this page.

## A large range doesn't freeze the program

A multi-day range can be hundreds of thousands of database rows.
Loading one runs on a background thread — the interface stays
responsive, and a "Loading..." message shows while it's working. Before
drawing, the data is reduced to roughly the number of points the chart
can actually show at its current width - the exact values are still
fetched from the database (nothing outside the requested time range and
tags is ever read), just not all individually rendered.

## Exporting

**Export visible range...** opens the same CSV export dialog as
**Tools → Export Historical Data...**, already set to the chart's
current time window and selected tags - see
[Exporting Historical Data](help://hist_export) for what the CSV
contains.
