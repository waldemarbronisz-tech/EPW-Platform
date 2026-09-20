# Check Project

It looks for the mismatches no single table can show, because they span
**two departments at once**. Double-click an entry to jump straight to
the problem.

The summary separates **Errors** from **Warnings**.

## What it checks

| Entry | What it means |
|---|---|
| an apparatus points at a point that is not in the registry | the point was deleted, or the address is a typo |
| an apparatus points at a point on a card no longer in the composition | the card is gone, the assignment stayed |
| **a point assigned to more than one apparatus** | two apparatus would drive the same output |
| a point names a location that is not on the list | the location was removed or renamed |
| a supervised line points at a point that does not exist | the line has nothing to watch |
| a process protection points at a point that does not exist | as above |
| a process protection points at a **non-AI** point | thresholds need an analog value |
| a module has data but is outside the composition | **a warning**: the branch is hidden, the data untouched |
| a pulsing style with a 0 ms pulse | a zero-length pulse does nothing |
| `PULSE_TOGGLE` with no feedback | every pulse toggles, so the state must be known |
| `PULSE_TOGGLE` with more than two outputs | this style takes one or two |

## When to run it

Before every send. The controller will accept a project that has not
passed this check — the format is valid, so there are no grounds to
refuse it — but an apparatus pointing at a point that does not exist
simply will not work, and you will find that out at the cabinet rather
than at the desk.
