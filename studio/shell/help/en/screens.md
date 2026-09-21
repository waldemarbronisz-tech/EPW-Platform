# Synoptic Diagram

The screen editor (Synoptic Editor) as a Studio department. You draw
what the operator will see on the controller — and bind the drawing to
real points and apparatus.

## What is made here

- **Apparatus symbols** bound by `deviceId` to the [apparatus
  registry](help://apparatus). A symbol shows the state from the
  feedback and takes a click as a command.
- **Wires and nets** — the colour follows the state: a net fed from a
  boundary point, or from the terminal of an apparatus whose feedback
  says "closed".
- **Measurements** — gauges, tanks and numeric readouts bound to analog
  points, with the unit and decimals from the [point
  registry](help://points).
- **Walls, rooms, openings** — the floor plan; the controller draws them
  the same way, with the same pseudo-3D extrusion.

## What the panel shows

Not the whole blue canvas (24 × 13.5 m by default — one 6 × 4 m
warehouse would be a stamp on it), but what is drawn, fitted into the
panel's window with a small margin. To decide the framing yourself: zoom
and pan until the plan looks as it should at the cabinet, then pick
**View → Runtime frame → Set from what I see now**. An orange dashed
frame labelled PANEL appears on the plan — exactly what the controller
will show. The frame is per screen; **Clear the frame** returns to the
automatic fit.

In the room inspector X and Y are the room's top-left corner measured
from the plan's top-left corner, and width and length are its size in
plan — all in metres.

## The screen lives in the project

There is no separate file to upload. The screen travels inside
`projekt.epw` and it is the controller's **Main View**. When a project
carries several screens, the panel gets a selector.

The editor document's own lifecycle (open/save `.epwsyn`) is on **this
department's contextual toolbar**, not on the top one — the top toolbar
always acts on the project.

## Points and cards are visible immediately

The editor uses the same point registry as the rest of Studio. If the
address lists are empty it means there are no [cards](help://io_cards)
yet — the warning stands next to the field itself, with a "+ Card"
button.

## Live mode

Once connected to a controller the symbols in the editor show the real
state — the same switch as in the [point registry](help://points).
