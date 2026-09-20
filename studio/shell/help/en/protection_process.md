# Process Protection

Thresholds on analog points, evaluated **on the controller**, live.
Boiler temperature, pressure, a tank level.

On the left the list of protections, on the right the selected one's
configuration.

| Field | Meaning |
|---|---|
| **Id / Name** | identifier and a readable name |
| **Point** | an **analog (AI)** point — any other kind is reported by [Check Project](help://validation) |
| **Upper threshold** | above this the protection is exceeded |
| **Lower threshold** | below this it is exceeded too |
| **Hysteresis** | how far the value must come back before it stops being exceeded |
| **Delay (s)** | how long the excursion must last before the protection acts |
| **En.** | whether the protection is enabled |

Thresholds are in the point's **engineering units** — the ones from the
[point registry](help://points), not the card's raw values.

## What happens on the controller

The protection publishes a `Process.<id>.Exceeded` tag. What should then
happen — closing a valve, stopping a pump, raising an alarm — is a line
of [logic](help://logic), not a setting here.

Hysteresis and delay exist so that a value hovering on the threshold
does not flip the protection back and forth.

## Verification

**[Protection Tests](help://protection_tests)** can check this without
taking the installation apart: it forces the value past the threshold,
times the trip against the configured delay, then brings it back in band
and times the reset.
