# The Governing Principle: "The Screen Informs, the Hardware Protects"

This is the single most important principle EPW OS is built on — worth
understanding before trusting anything the screen shows.

**EPW OS is not a protection system for the installation, and it is
never required for a protection function to work.**

The program runs in Python on a computer (Orange Pi) — it can hang,
lose power, or have a bug. The installation's real protection is
provided by electrical protection devices and an independent hardware
safety path — these keep working even if EPW OS stops working entirely.

EPW OS's role is to:

- **show** the state of the installation and its protection on screen,
- **record** events and alarms,
- **assist** manual control, with sensible interlocks in place.

EPW OS's role is NOT to:

- be the only mechanism standing between the installation and a fault,
- decide on its own to shut down the installation in response to a
  detected problem.

This principle has direct consequences in the program's code — see
[System Health Monitoring (safety_kernel)](help://saf_kernel), which
describes exactly where the line between "detecting" and "reacting" is
drawn.
