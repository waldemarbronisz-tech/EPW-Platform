# What This Panel May Change in the Project

Not everything in `projekt.epw` is equal. The split decides what can be
corrected at the cabinet and what has to go back through Studio.

## A setting — yes

A value of something that already exists: a zone's entry and exit
delays, a supervised line's filters, a protection's thresholds, an
analog point's scaling, the MQTT settings, the sounder's sounding time.

Changing one here writes it **into the project file**, raises its
revision and records the change in the audit log as coming from the
panel. Studio then sees the difference and can take it into the project
— so a correction made at three in the morning is not lost the next time
somebody sends from a laptop.

## Structure — no

What exists at all: cards, points, apparatus, the device composition,
zones, lines, screens, the logic. This panel **refuses** to change those
and writes the refusal to the audit log.

That is not a limitation to work around. A controller whose composition
can drift at the cabinet is a controller whose drawing no longer
describes it.

## The revision

Every save raises it and records who saved: Studio or the panel. It is
how [installing a project](help://proj_install) can tell that this
controller holds something newer than the laptop does — and stop,
instead of overwriting somebody's work.

## What is never in the project

PINs, alarm users' keypad codes, remote tokens and the MQTT broker
password. Those belong to **this controller**, not to the installation,
and live in its own local files, stored one-way. A project travels to
Studio, into version control and over the network; secrets do not
travel.
