# Object Links

One controller's point, available on another. Over MQTT: the source
publishes its tags, the target subscribes to them.

You need a saved [object with at least two
controllers](help://site).

| Column | Meaning |
|---|---|
| **Source** | the controller that has the value |
| **Source point** | its point |
| **Target** | the controller that should see it |
| **`Link.*` tag on the target** | what it will be called there: `Link.<Id>.In<name>` |
| **Type** | the value's type |
| **Stale after** | how long without a refresh before it counts as stale |

## What Studio does for you

It writes the incoming mapping into the target controller's
[MQTT](help://mqtt) settings and, if needed, enables MQTT there and
gives it a topic prefix. Removing a controller from the object takes its
links with it.

Mappings entered by hand are **never** touched.

## What a `Link.*` tag is, and what it is not

A `Link.*` tag works in the target's [logic](help://logic) and
[screens](help://screens) like any other tag — but it is **a value to
read, only**. It is never a command: you cannot operate another
controller's apparatus through it.

There is no cross-project addressing on screens either — the target's
screen binds a symbol to a `Link.*` tag exactly as it would to any
other.
