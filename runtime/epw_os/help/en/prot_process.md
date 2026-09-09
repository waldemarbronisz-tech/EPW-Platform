# Process Protections

A minimal, from-scratch module: pick an existing **Analog Input**
point, set an **upper** and **lower threshold**, an optional
**hysteresis**, and an optional **delay** — that's the whole
configuration. Unlike Electrical Protections, this one actually
evaluates live: the moment the bound point's value goes outside the
[lower, upper] band, past its hysteresis and delay, the protection
reads **Exceeded**.

- **Hysteresis** — how far back *inside* the band the reading has to
  return before Exceeded clears. Prevents chatter when a reading sits
  right at the threshold. Clearing itself is always immediate, no
  delay.
- **Delay** — how long the reading has to stay outside the band before
  Exceeded actually latches. Filters a brief spike or glitch; 0 =
  latches the instant the band is crossed.
- **Enabled** — a protection can be temporarily disabled without
  deleting it; a disabled protection never reads Exceeded, regardless
  of the live value.

Like every other alarm/supervision module in this program, this one
**never drives an output**. It only publishes a read-only signal tag,
`Process.<id>.Exceeded`, for a logic program to react to however the
installation needs — sound an alarm, start a fan, whatever's
appropriate. The reaction itself is entirely up to that logic.

Adding, editing, or removing a protection requires **Engineer** level;
viewing the table needs no particular level.

This page didn't exist before — there was no working process-threshold
feature anywhere in the program prior to it (see
[Electrical vs. Process Protections](help://prot_what) for why the old
page's own Environmental category doesn't count as a predecessor).
