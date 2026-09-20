# Alarm System Users

The three [access levels](help://al_three) could never answer "only
Kowalski may disarm the warehouse" — two operators are the same Operator
to them. Named users can.

## Who exists, and who says so

The **people** come from the project: an id, a name, the level their own
code grants, and the zones they may operate (an empty list means every
zone). That is designed in Studio.

Their **secrets** belong to this controller. **Settings → Alarm system
users** (Engineer) is where you:

- **set a keypad code** — typed twice, stored one-way, never readable
  again;
- **clear it** — the person stays, they simply cannot sign in;
- **issue a remote token** — for commanding this controller over
  [MQTT](help://mqtt_commands). It is shown **once**;
- **revoke it** — which does not touch their keypad code.

Issuing a new token replaces the old one immediately. That is how a
leaked token is dealt with.

## A token is not a code

Two separate secrets of the same person. The token sits in a Home
Assistant automation on another machine; if it were the same code, a
leak from there would open the panel at the cabinet. Revoking one does
not touch the other.

## What this changes in the record

With nobody signed in as a person, the log says "Panel:Operator". With a
person's code, it says their name: "Kowalski disarmed zone Hall".
Refusals too — not their zone, a disabled account, an unknown code — all
of it lands in the audit log and in the [alarm
history](help://intr_history).

## Why the code is not in the project

`projekt.epw` travels to Studio, into version control and over the
network. Codes and tokens are secrets of this one controller, so they
stay in its own local file, under the user's id.

The consequence is worth knowing: **a person exists the moment the
project lands, and can sign in the moment somebody sets their code
here.**
