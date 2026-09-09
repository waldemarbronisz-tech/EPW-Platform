# Forcing an Output State (Force) and Why It Requires Engineer

There are TWO different forcing features in the program — deliberately
different, for different purposes.

## Force in Control Outputs

Every controllable output has a **Force** button. Clicking it opens a
confirmation, and once confirmed the command goes through **exactly the
same mechanism** as normal control from Main View (including the safety
checks) — the only difference is you don't need to go to the one-line
diagram to use it. It works in both simulation and live mode. This is a
commissioning/service tool, which is why it requires the Engineer
level, while normal control from Main View only needs Operator.

## Forcing in Digital Inputs (context menu)

Right-clicking a row in Digital Inputs opens a menu with Force ON /
Force OFF / Toggle / Pulse. **This only works in simulation mode** — it
directly sets the input tag's value, as if the signal had actually come
in from the installation. It's used to test logic and visualization
without connected hardware. It requires the Engineer level.

Both features are unavailable (buttons/menu disabled or hidden) below
the required level, and any attempt to use them is checked again at the
moment they actually execute.
