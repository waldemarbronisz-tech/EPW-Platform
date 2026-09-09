# Configuration: Signal Type, Ranges, Unit, Decimal Places

Full configuration opens with the **Configure** button on the point's
row (Engineer). Description, unit, and technical note are NOT edited
here anymore — those three fields are edited directly in the table
(double-click), the same way described in
[Setting Descriptions](help://dio_descriptions) for digital
inputs/outputs.

## Signal Type

Four options:

- **4-20mA** — standard current loop
- **0-10V** — standard voltage
- **0-3.3V ADC (raw)** — raw signal from an A/D converter
- **Ready value (no conversion)** — the tag's value already is the
  engineering value, with no conversion at all (this is the default for
  a new point)

For the first three types, the **raw range** field is automatically
filled with the typical values for that signal (e.g. 4–20 for a current
loop) — these can be freely changed afterwards.

## Ranges

The **raw range** is the range of the physical signal's values (e.g.
4–20 mA). The **engineering range** is the range of the value shown on
screen after conversion (e.g. 0–100 °C). The program linearly converts
the raw value into the engineering value between these ranges. Both
ranges are hidden and irrelevant for the "Ready value" type — in that
case the tag's value is shown as-is, with no conversion.

## Decimal Places

The number of digits after the decimal point shown in the Value column
— purely cosmetic, it does not affect the accuracy of the stored data.

## Tag / Address

Visible in this window, but only editable when creating a new point —
see [Adding and Removing Points](help://ap_add_remove).
