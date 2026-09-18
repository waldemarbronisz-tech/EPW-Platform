# EPW Studio

EPW Studio is a single engineering application for designing EPW
platform installations: synoptic diagram, control logic, point
registry, apparatus, intrusion alarm, protection settings, and the
controller connection — all in one window, one project tree.

**Screens (Synoptic Editor) and Logic (Logic Studio) are departments of
Studio**, not separate programs — launching each one standalone is no
longer how this is used.

**Object and devices.** The left column starts with the DEVICE LIST:
an object (a house, a plant) and its controllers, each its own
`projekt.epw` in its own folder, tied together by an `obiekt.epwsite`
file (File → New Object / Open Object / Add Controller to Object).
Clicking a controller switches the whole tree below to its project; a
controller with unsaved edits is red with an asterisk. "Save" saves the
active controller, "Save Object" saves them all. A plain single
`projekt.epw` still works as before, as a one-controller object.

**The project tree shows where unsaved edits are**: a branch you
edited is red with an asterisk (`Locations *`) until the project is
saved. The root carries the project's name (EntryGate, MainHouse...) -
double-click renames it in place, the same field as in Project
Information.

Pick a topic from the list on the left to learn more about a specific
department.
