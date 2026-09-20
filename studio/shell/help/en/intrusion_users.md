# Alarm System Users

Who may arm and disarm which zones — by name.

The three access levels (User / Operator / Engineer) could never answer
"only Kowalski may disarm the warehouse": two operators are the same
Operator to them. This register can.

| Column | Meaning |
|---|---|
| **Id** | the person's identifier, e.g. `U1` — their secrets live under it on the controller |
| **Name** | what appears in the log instead of "Panel:Operator" |
| **Level** | the access level their own code grants |
| **Zones** | which ones they may operate; **an empty list = all of them** |
| **Active** | unticking disables the account without deleting it |

## The code is not here, and never will be

`projekt.epw` travels to Studio, into git and over the network. The
keypad code and the remote token are secrets of **one controller** —
they live in its own access file, under the user's id, stored one-way.

Hence the order of work: **a person exists the moment the project lands
on the controller, and can sign in the moment somebody sets their code
on the panel** (Settings → Alarm system users, Engineer level). That is
also where a **remote token** for [MQTT](help://mqtt) is issued — shown
once; a token is not a code, so a leak from Home Assistant does not open
the panel at the cabinet.

## What this changes in the log

The log says "Kowalski disarmed zone Hall", not "Panel:Operator".
Refusals too: not their zone, a disabled account, an unknown code — all
of it goes to the audit log and the alarm history.
