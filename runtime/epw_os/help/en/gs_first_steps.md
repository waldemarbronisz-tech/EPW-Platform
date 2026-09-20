# A New Controller, Step by Step

What to do, in order, with a controller that has just been installed in
a cabinet. Each step links to the page that explains it properly.

## 1. Check what is actually running

The status bar, left to right: the work mode, communications, the
[logic indicator](help://logic_state), the alarm system's state,
[forces](help://dio_force), the clock. Any startup problem is reported
in a window when the program opens — read it rather than closing it.

## 2. Put the project on it

**File → Open** — see [Installing a Project](help://proj_install). The
controller rebuilds itself from the new file without restarting, so this
is also how you correct a project later.

## 3. Set the PINs

[Access levels](help://al_three) are Operator and Engineer, each with
its own PIN. Change them from the defaults before anybody else uses the
panel — [Changing a PIN](help://al_change_pin).

## 4. Give the alarm system its people

**Settings → Alarm system users** (Engineer) — the people come from the
project; here you give each one a **keypad code**, and a **remote
token** if they are to command the controller from Home Assistant. See
[Alarm System Users](help://intr_users).

## 5. Walk the lines

Before arming anything for real: [walk-test
mode](help://intr_walk_test) shows which lines actually see a person
walking past them, without raising an alarm. A detector that was never
walked is a detector nobody has checked.

## 6. Check the supervision

[Power supervision](help://intr_power_supervision) — mains and battery.
[Line life](help://intr_line_life) — a line that has been silent for too
long is marked suspect.

## 7. Wire the sounder in the logic

The controller drives no siren; it publishes the state. See [The
Sounder](help://intr_sounder) and [What the Logic Program Can
See](help://logic_signals). Nothing sounds until you draw that line.

## 8. Connect the integrations

[MQTT](help://mqtt_what) for Home Assistant, and if it is to **command**
this controller, [Control from Home Assistant](help://mqtt_commands).

## 9. Then arm it

[Arming and disarming](help://intr_arming), and [night
arming](help://intr_night) if people are to move about inside while the
perimeter watches.

## 10. Leave a record

[Service notes](help://dio_service_notes) are the logbook — what was
found, what was replaced, what was left half-done. Entries are never
edited or deleted, and they travel back to Studio with the project.
