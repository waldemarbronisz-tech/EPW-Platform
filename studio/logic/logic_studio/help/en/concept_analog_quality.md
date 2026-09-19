# Analog signal quality

The [QUALITY](help:block:analog.quality) block and the `Quality` output
of the [AI](help:block:input.ai) block watch whether an analog
measurement can be trusted at all, before safety logic starts relying on
it.

## What the Quality output is for

`Quality`/`Good` is true only when the reading is a NUMBER (not NaN or
Inf), lies within the measuring range, does not change faster than the
permitted rate of change, and is not "frozen" (see Stuck below). This
output is marked **safety relevant** — logic driving critical outputs
should check it before trusting the measured value, not just the value
itself.

## Why Stuck Tolerance MUST be greater than zero on a real measuring chain

Detecting a "frozen" signal (Stuck) works by comparing two consecutive
readings. With the default `Stuck Tolerance = 0.0` (exact equality), a
signal from a REAL analog-to-digital converter will practically never be
judged frozen — noise in the converter's last bit means two consecutive
samples are almost never bit-identical, even when the measured quantity
is not physically changing. The effect: stuck detection does NOT really
work until `Stuck Tolerance` is set above zero. A starting point: about
0.1% of the measuring range — tight enough to catch a genuinely frozen
signal, loose enough that ordinary converter noise does not defeat the
detection every scan.

## What Max Hold (ms) does

While `Quality` is false, the AI block holds the LAST good value on its
`Value` output (fail-safe: logic keeps running on trustworthy if slightly
stale data rather than on garbage). With no time limit, that "last good
value" could be held for hours or days if nothing happens to be watching
`Quality`. `Max Hold (ms)` bounds it in time — once exceeded, `Hold
Expired` (also safety relevant) becomes true and `Value` switches to
whatever the `Hold Timeout Value` property selects (zero, the last good
value, or the bottom of the range). `Max Hold (ms) = 0` means no limit —
behaviour identical to what it was before this property existed.
