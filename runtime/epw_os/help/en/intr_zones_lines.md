# Zones and Supervision Lines

A **supervision line** is one existing tag (typically a Digital Input,
but any tag works) bound to:

- a name you choose
- which zone it belongs to
- its **normal (secure) state** — Normally Closed (the tag reads True
  when secure, False when tripped) or Normally Open (the reverse)
- a **line type** — see [Line Types](help://intr_line_types)

A **zone** is a named group of lines, armed and disarmed together, with
its own exit delay and entry delay (in seconds).

There is no fixed number of zones or lines, and no assumption about
which physical inputs they use — add and configure as many as your
installation needs from **Configure Zones** / **Configure Lines** on
the Configuration page (Engineer level - the whole page, not just
these two buttons).
